# ParameterServer
Parameter Server with bounded delay is based on FALCON. The initisl code is available [here] (https://github.com/kimihe/Falcon/tree/master/SSP_Demo)

A computation-parallel deep learning architecture.

# Quick Start
To run the SSP with MnistCNN dataset:

If you do not have access to multiple remote devices, then you can actually do this locally. 

 

* This is an example with one server and 5 workers with varying delay values (Can adjust slow values by setting "slow" argument):
```
python param_server.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=0 --learners=1-2-3-4-5 --epochs=10 --model=MnistCNN --stale-threshold=0
```

* Start workers, here we will start 10 workers, each one is started individualy on a seperate terminal:
```
python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=1 --learners=1-2-3-4-5 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.2

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=2 --learners=1-2-3-4-5 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.3

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=3 --learners=1-2-3-4-5 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.4

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=4 --learners=1-2-3-4-5 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.5

python learner.py --ps-ip=127.0.0.1 --ps-port=29500 --data-dir=~/Data/Mnist --this-rank=5 --learners=1-2-3-4-5 --model=MnistCNN --epochs=10 --save-path=~/Data/Mnist/output --slow=0.6

```

* the key parameters to changes are in the command line are :
1. learners : number of workers to start, each one should have a different rank if started Synchronosly
2. model : dataset
3. stale-threshold varies, in case of Sync Parameter Server, the value is 0, for Async Parameter Server the value is very big to ensure it is never reached
4. slow: a delay that needs to be different from one worker to another in case of sync parameter server for example

# How to change staleness value
* In the param_server.py file, change the "staleValue" global value. 
* Spectral Clustering- Set staleValue to GenerateTopKEigenValues
* GMM, go to mnist-em-bmm-gmm folder and run python __main__.py --path="Path to MNIST" and it will output the average of the covariances. Set staleValue to the inverse of the average of the covariances
* Epoch based, increment staleValue by however the user may want per epoch.
* For weights based, set the staleValue by T X np.sum(delta_ws[0]) value. The can set the T value, but we noticed that T=100 worked the best. 


# Dataset
* MNIST: This demo has already contained MNIST in the directory `data`, you can also download it from [http://yann.lecun.com/exdb/mnist/](http://yann.lecun.com/exdb/mnist/)
* CIFAR-10: You can download it from [https://www.cs.toronto.edu/~kriz/cifar.html](https://www.cs.toronto.edu/~kriz/cifar.html)


