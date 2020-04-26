# -*- coding: utf-8 -*-

import argparse
import os
import random
import sys
import time
import numpy as np
from collections import OrderedDict
from multiprocessing.managers import BaseManager
from gmm_mml import GmmMml
import matplotlib.pyplot as plt
import numpy as np
from sklearn.model_selection import train_test_split
import numpy as np
import torch

from gmm import GaussianMixture
from math import sqrt

import torch
import torch.distributed as dist
from utils.models import MnistCNN, AlexNetForCIFAR
from utils.utils_data import get_data_transform
from utils.utils_model import test_model
from torch.multiprocessing import Process as TorchProcess
from torch.multiprocessing import Queue
from torch.utils.data import DataLoader
from torchvision import datasets

from scipy.spatial import distance
from sklearn.metrics.pairwise import rbf_kernel
from scipy.sparse import csgraph
from scipy import linalg, spatial


parser = argparse.ArgumentParser()
# 集群基本信息的配置 - The basic configuration of the cluster
parser.add_argument('--ps-ip', type=str, default='127.0.0.1')
parser.add_argument('--ps-port', type=str, default='29500')
parser.add_argument('--this-rank', type=int, default=0)
parser.add_argument('--learners', type=str, default='1-2')

# 模型与数据集的配置 - The configuration of model and dataset
parser.add_argument('--data-dir', type=str, default='../../data')
parser.add_argument('--model', type=str, default='MnistCNN')

# 训练时各种超参数的配置 - The configuration of different hyper-parameters for training
parser.add_argument('--timeout', type=float, default=10000.0)
parser.add_argument('--len-train-data', type=int, default=60000)
parser.add_argument('--epochs', type=int, default=1)
parser.add_argument('--stale-threshold', type=int, default=1000)

args = parser.parse_args()


def run(model, test_data, queue, param_q, stop_signal):
    if args.model == 'MnistCNN':
        criterion = torch.nn.NLLLoss()
    else:
        criterion = torch.nn.NLLLoss()

    # 参数中的tensor转成numpy - convert gradient tensor to numpy structure
    tmp = map(lambda item: (item[0], item[1].numpy()), model.state_dict().items())
    _tmp = OrderedDict(tmp)
    workers = [int(v) for v in str(args.learners).split('-')]
    for _ in workers:
        param_q.put(_tmp)

    print('Begin!')

    epoch_train_loss = 0
    iteration_in_epoch = 0
    data_size_epoch = 0   # len(train_data), one epoch
    epoch_count = 0
    staleness_sum_suqare_epoch = 0
    staleness_sum_epoch = 0

    staleness = 0
    learner_staleness = {l: 0 for l in workers}
    s_time = time.time()
    epoch_time = s_time

    # Used to keep track of running average of an epoch from a workers
    # e_epoch_time - s_time / count[rank_src] to compute the mean
    count = {l: 0 for l in workers}

    
    # In SSP, the fast workers have to wait the slowest worker a given duration
    # The fast worker exceeding the duration will be pushed into the queue to wait
    stale_stack = []

    trainloss_file = './trainloss' + args.model + '.txt'
    staleness_file = './staleness' + args.model + ".txt"

    if(os.path.isfile(trainloss_file)):
        os.remove(trainloss_file)
    if(os.path.isfile(staleness_file)):
        os.remove(staleness_file)
    f_trainloss = open(trainloss_file, 'a')
    f_staleness = open(staleness_file, 'a')
    while True:
        if not queue.empty():
            tmp_dict = queue.get()
            rank_src = list(tmp_dict.keys())[0]
            count[rank_src] += 1

            isWorkerEnd = tmp_dict[rank_src][3]
            if isWorkerEnd:
                print("Worker {} has completed all its data computation!".format(rank_src))
                learner_staleness.pop(rank_src)
                if (len(learner_staleness) == 0):
                    f_trainloss.close()
                    f_staleness.close()
                    stop_signal.put(1)
                    print('Epoch is done: {}'.format(epoch_count))
                    break
                continue

            delta_ws = tmp_dict[rank_src][0]  # 取出字典：k：参数索引 v：delta_w - dictionary: key parameter index, value: v：delta_w(gradient)
            iteration_loss = tmp_dict[rank_src][1]
            batch_size = tmp_dict[rank_src][2]

            iteration_in_epoch += 1
            epoch_train_loss += iteration_loss
            data_size_epoch += batch_size
            # t = np.array(delta_ws)
            # print(len(delta_ws[0]))
            for idx, param in enumerate(model.parameters()):
                print(np.sum(delta_ws[idx]))
                param.data -= torch.from_numpy(delta_ws[idx])
                

            stale = int(staleness - learner_staleness[rank_src])
            staleness_sum_epoch += stale
            staleness_sum_suqare_epoch += stale**2
            staleness += 1
            learner_staleness[rank_src] = staleness
            stale_stack.append(rank_src)
            print("Staleness is: ", staleness, " Map is: ", learner_staleness)
            # judge if the staleness exceed the staleness threshold in SSP
            outOfStale = False
            for stale_each_worker in learner_staleness:
                if (stale_each_worker not in stale_stack) & \
                    (staleness - learner_staleness[stale_each_worker] > args.stale_threshold):
                    outOfStale = True
                    break
            if not outOfStale:
                for i in range(len(stale_stack)):
                    rank_wait = stale_stack.pop()
                    # 相应learner下次更新的staleness - SSP: staleness upadate
                    learner_staleness[rank_wait] = staleness
                    for idx, param in enumerate(model.parameters()):
                        dist.send(tensor=param.data, dst=rank_wait)
            else:
                continue

            #print('Done From Rank {}, Staleness {}!'
            #      .format(rank_src, stale))
            # epoch, rank, batch size, stale
            f_staleness.write(str(epoch_count) +
                        "\t" + str(rank_src) +
                        "\t" + str(batch_size) +
                        "\t" + str(stale) + '\n')

            # once reach an epoch, count the average train loss
            if(data_size_epoch >= args.len_train_data):
                e_epoch_time = time.time()
                #variance of stale
                diversity_stale = (staleness_sum_suqare_epoch/iteration_in_epoch)\
                                 - (staleness_sum_epoch/iteration_in_epoch)**2
                staleness_sum_suqare_epoch = 0
                staleness_sum_epoch = 0
                test_loss, test_acc = test_model(dist.get_rank(), model, test_data, criterion=criterion)
                # rank, trainloss, variance of stalness, time in one epoch, time till now
                f_trainloss.write(str(args.this_rank) +
                                  "\t" + str(epoch_train_loss/float(iteration_in_epoch)) +
                                  "\t" + str(diversity_stale) +
                                  "\t" + str(e_epoch_time - epoch_time) +
                                  "\t" + str(e_epoch_time - s_time) +
                                  "\t" + str(epoch_count) +
                                  "\t" + str(test_acc) + '\n')
                s = torch.sum(model.conv1.weight.data)
                f_trainloss.flush()
                f_staleness.flush()
                iteration_in_epoch = 0
                epoch_count += 1
                epoch_train_loss = 0
                data_size_epoch = 0
                epoch_time = e_epoch_time

            # The training stop
            if(epoch_count >= args.epochs):
                f_trainloss.close()
                f_staleness.close()
                stop_signal.put(1)
                print('Epoch is done: {}'.format(epoch_count))
                break

        e_time = time.time()
        if (e_time - s_time) >= float(args.timeout):
            f_trainloss.close()
            f_staleness.close()
            stop_signal.put(1)
            print('Time up: {}, Stop Now!'.format(e_time - s_time))
            break

def init_processes(rank, size, model, test_data, queue, param_q, stop_signal, fn, backend='gloo'):
    os.environ['MASTER_ADDR'] = args.ps_ip
    os.environ['MASTER_PORT'] = args.ps_port
    dist.init_process_group(backend, rank=rank, world_size=size)
    fn(model, test_data, queue, param_q, stop_signal)


def ComputeLaplacian(training_dataset, random_size=1000):

    data_loader = DataLoader(training_dataset, batch_size=random_size, shuffle=True)

    inputs, _ = next(iter(data_loader))
    matrix_size = len(inputs)
    Sim_Matrix = np.zeros((matrix_size, matrix_size))
    
    for i, val_i in enumerate(inputs):
        for j, val_j in enumerate(inputs):

            #Several similarity distance functions... Used cosine similarity
            t = 1 - spatial.distance.cosine(val_i[0].flatten(), val_j[0].flatten())
            # t = distance.euclidean(val_i[0].flatten(), val_j[0].flatten())
            # dist = np.linalg.norm(val_i[0].flatten()-val_j[0].flatten())
            # t = np.exp(-dist**2/(2.*(sigma**2.)))
            # print(t)
            Sim_Matrix[i][j] = t

    lap = (csgraph.laplacian(Sim_Matrix, normed=False))
    val, vec = linalg.eigh(lap)
    for i in range(len(val)):
        print("Val: ", val[i])
    
    # similarity_matrix = [[0.0] for j in range(len(training_data))]
    # pairwise_dists = squareform(pdist(training_data[0], 'euclidean'))
    # K = scip.exp(-pairwise_dists ** 2 / s ** 2)
    # print(K)
    
    
    
if __name__ == "__main__":

    # 随机数设置 - Random
    manual_seed = random.randint(1, 10000)
    random.seed(manual_seed)
    torch.manual_seed(manual_seed)

    if args.model == 'MnistCNN':
        model = MnistCNN()
        train_t, test_t = get_data_transform('mnist')
        train_dataset = datasets.MNIST(args.data_dir, train=True, download=False,
                                      transform=train_t)
        test_dataset = datasets.MNIST(args.data_dir, train=False, download=False,
                                      transform=test_t)
    elif args.model == 'AlexNet':
        model = AlexNetForCIFAR()
        train_t, test_t = get_data_transform('cifar')
        test_dataset = datasets.CIFAR10(args.data_dir, train=False, download=False,
                                        transform=test_t)
    else:
        print('Model must be {} or {}!'.format('MnistCNN', 'AlexNet'))
        sys.exit(-1)
    
    test_data = DataLoader(test_dataset, batch_size=100, shuffle=True)
    # ComputeLaplacian(train_dataset)

    #GMM ----- 
    #model = GaussianMixture(28, 28)
    #model.fit(test_dataset.data)
    #GMM end
    world_size = len(str(args.learners).split('-')) + 1
    this_rank = args.this_rank

    queue = Queue()
    param = Queue()
    stop_or_not = Queue()


    class MyManager(BaseManager):
        pass


    MyManager.register('get_queue', callable=lambda: queue)
    MyManager.register('get_param', callable=lambda: param)
    MyManager.register('get_stop_signal', callable=lambda: stop_or_not)
    manager = MyManager(address=(args.ps_ip, 5000), authkey=b'queue')
    manager.start()

    q = manager.get_queue()  # 更新参数使用的队列 - queue for parameter_server signal process
    param_q = manager.get_param()  # 开始时传模型参数使用的队列 - init
    stop_signal = manager.get_stop_signal()  # 传停止信号使用的队列 - stop

    p = TorchProcess(target=init_processes, args=(this_rank, world_size, model,test_data,
                                                  q, param_q, stop_signal, run))
    p.start()
    p.join()
    manager.shutdown()