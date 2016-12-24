# -*- coding:utf-8 -*-
# @Author: gzliwenfeng<gzliwenfeng@corp.netease.com>
# @Description: 协程测试
__author__ = 'gzliwenfeng'

import time
import coroutine
from functools import partial

sleep = coroutine.sleep
def sleep1():
	print 'sleep1 start', time.time()
	sleep(0.5)
	print 'sleep1 over', time.time()

def sleep2():
	print 'sleep2 start', time.time()
	sleep(3)
	print 'sleep2 over', time.time()

def sleep3():
	print 'sleep3 start', time.time()
	sleep(3)
	print 'should never print'

def test_join(co1, co2):
	print 'wait.......', time.time()
	coroutine.join((co1, co2))
	print 'co1, co2 end', time.time()
	#raise TypeError('raise type error')

def main():
	coroutine.run(test)

def test():
	co1 = coroutine.spawn(sleep1)
	print 'create co1', time.time()
	co2 = coroutine.run(sleep2)
	print 'create co2', time.time()
	co3 = coroutine.spawn(test_join, co1, co2)
	print 'create co3', time.time()
	killco = coroutine.run(sleep3)
	coroutine.kill(killco)
	print 'killco killed: %s %s' % (killco.dead, time.time())
	coroutine.join((co3, killco))
	print 'co3, killco end', time.time()
	sleep(2)
	print 'over', time.time()
	coroutine.test_stop()

def create_garbage():
	p1 = coroutine.Promise()
	p2 = coroutine.Promise()
	p1.p = p2
	p2.p = p1

def test1():
	import gc
	gc.set_debug(gc.DEBUG_SAVEALL)
	print gc.garbage
	#create_garbage()
	coroutine.test_run(30.0, main)
	gc.collect()
	print gc.garbage

if __name__ == '__main__':
	test1()
