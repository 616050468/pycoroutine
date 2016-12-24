## pycoroutine

一个轻量级的python协程库的封装，使用greenlet，不依赖于底层的网络驱动，纯粹的协程调度管理，并加入了Promise/A+规范，可以方便地接入到已有项目中。
自带定时器功能，需要也可以替换成自己的。

只支持单线程

## 接口

import coroutine

> run

创建一个协程，并马上执行，返回协程对象

> spawn

创建一个协程，马上返回协程对象，协程会在之后某个时刻开始执行

> kill

停止一个协程，可同步等待协程结束，也可以不关心马上返回，协程会在以后某个时刻被终止掉

> join

等待协程（可以多个）终止

> sleep

协程睡眠一段时间继续执行

## 使用

import coroutine

程序启动时调用coroutine.GreenletMgr.init(on_traceback)， 参数为发生异常时的回调处理，默认输出到控制台

在代码loop的地方加入coroutine.loop()

在每帧update的时候加入 coroutine.update()

具体可以看test.py中的例子 （需要安装greenlet）

## 单元测试

安装nose， 运行nosetests test_coroutine.py, nosetests test_promise.py

## 声明

自己在python 2.7.9上使用的，不过在其他更高版本中应该问题也不大

## todo

支持python原生的yield
