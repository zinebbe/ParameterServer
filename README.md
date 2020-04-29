# ParameterServer
Parameter Server with bounded delay is based on FALCON. The initisl code is available [here] (https://github.com/kimihe/Falcon/tree/master/SSP_Demo)

A computation-parallel deep learning architecture.

# Quick Start
To run the SSP with MnistCNN dataset:

* Start the Parameter Server specifing the number of learners to expect, here we will start one sever and 10 workers:
```
python param_server.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=0 --learners=1-2-3-4-5-6-7-8-9-10 --epochs=10 --model=MnistCNN --stale-threshold=0
```

* Start workers, here we will start 10 workers, each one is started individualy on a seperate terminal:
```
python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=1 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.2

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=2 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.3

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=3 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.4

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=4 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.5

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=5 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.6

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=6 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.7

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=7 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.8

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=8 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.9

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=9 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=1

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=10 --learners=1-2-3-4-5-6-7-8-9-10 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=1.2
```

* the key parameters to changes are in the command line are :
1. learners : number of workers to start, each one should have a different rank if started Synchronosly
2. model : dataset
3. stale-threshold varies, in case of Sync Parameter Server, the value is 0, for Async Parameter Server the value is very big to ensure it is never reached
4. slow: a delay that needs to be different from one worker to another in case of sync parameter server for example

* Apply GMM to the MNIST dataset

From mnist-em-bmm-gmm forlder, run the follwing:
```
python __main__.py --path="Your path to MNIST"
```

# Dataset
* MNIST: This demo has already contained MNIST in the directory `data`, you can also download it from [http://yann.lecun.com/exdb/mnist/](http://yann.lecun.com/exdb/mnist/)
* CIFAR-10: You can download it from [https://www.cs.toronto.edu/~kriz/cifar.html](https://www.cs.toronto.edu/~kriz/cifar.html)


