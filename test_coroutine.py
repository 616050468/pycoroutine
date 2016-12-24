# -*- coding:utf-8 -*-
# run cmd 'nosetests test_coroutine.py'
__author__ = 'gzliwenfeng'

from nose.tools import assert_equals, assert_is_instance
from functools import partial
import coroutine
import gc

sleep = coroutine.sleep

class TestEnv(object):
	def __init__(self):
		self.visitor = []
		self.state = None
		self.errmsg = ''
		self.timer_id = None

	def run(self, fun, timeout):
		self.timer_id = coroutine.Timer.addTimer(timeout, partial(self.fail, 'timeout'))
		fun(self)

	def success(self):
		if self.state is not None:
			return
		self.state = True
		coroutine.Timer.cancelTimer(self.timer_id)
		coroutine.test_stop()

	def fail(self, errmsg=''):
		if self.state is not None:
			return
		self.state = False
		self.errmsg = errmsg
		coroutine.test_stop()

def run_in_co(fun, timeout):
	gc.set_debug(gc.DEBUG_SAVEALL)
	env = TestEnv()
	fun = partial(env.run, fun, timeout)
	coroutine.test_run(30.0, partial(coroutine.run, fun))
	assert_equals(env.state, True, env.errmsg)
	gc.collect()
	assert_equals(len(gc.garbage), 0, 'some garbage created')
	#gc.set_debug(0)

def test_sleep_1():
	def sleep_1(env):
		sleep(0)
		sleep(1)
		env.success()
	run_in_co(sleep_1, 2.0)

def test_spawn_1():
	lst = [1]
	def spawn_1(env):
		co = coroutine.spawn(lst.pop)
		if len(lst) != 1:
			env.fail('len is not 1')
		else:
			sleep(0.1)
			env.success()
			if len(lst) == 0 and co.dead:
				env.success()
			else:
				env.fail('len is not 0 or co not dead')
	run_in_co(spawn_1, 1)

def test_run_1():
	lst = [1]
	def run_1(env):
		co = coroutine.run(lst.pop)
		if len(lst) == 0 and co.dead:
			env.success()
		else:
			env.fail('len is not 0 or co not dead')
	run_in_co(run_1, 1)

def test_kill_1():
	def be_kill(env):
		sleep(0.1)
		env.fail('should never be called')

	def run_1(env):
		co = coroutine.run(partial(be_kill, env))
		coroutine.kill(co)
		if co.dead:
			env.success()
		else:
			env.fail('co not killed')
	run_in_co(run_1, 1)

def test_kill_2():
	def be_kill(env):
		sleep(0.1)
		env.fail('should never be called')

	def run_1(env):
		co = coroutine.run(partial(be_kill, env))
		coroutine.kill(co, block=False)
		if not co.dead:
			coroutine.join((co, ))
			if co.dead:
				env.success()
			else:
				env.fail('co not killed')
		else:
			env.fail('co killed')
	run_in_co(run_1, 1)

def test_join_1():
	def joined_before_dead(env):
		env.visitor.append(1)

	def join_1(env):
		co1 = coroutine.spawn(partial(joined_before_dead, env))
		coroutine.join((co1, ))
		if co1.dead and len(env.visitor) == 1:
			env.success()
		else:
			env.fail()

	run_in_co(join_1, 1)


def test_join_2():
	def joined_after_dead(env):
		env.visitor.append(1)

	def join_1(env):
		co1 = coroutine.spawn(partial(joined_after_dead, env))
		sleep(0.1)
		if co1.dead and len(env.visitor) == 1:
			coroutine.join((co1, ))
			env.success()
		else:
			env.fail()

	run_in_co(join_1, 1)

def test_join_3():
	def joined_before_dead(env):
		env.visitor.append(2)

	def joined_after_dead(env):
		env.visitor.append(1)

	def join_1(env):
		co1 = coroutine.spawn(partial(joined_before_dead, env))
		co2 = coroutine.run(partial(joined_after_dead, env))
		if co2.dead and not co1.dead and len(env.visitor) == 1:
			coroutine.join((co1, co2))
			if co1.dead and env.visitor == [1, 2]:
				env.success()
			else:
				env.fail()
		else:
			env.fail()

	run_in_co(join_1, 1)


def test_kill_and_join_1():
	def be_kill(env):
		sleep(0.1)
		env.visitor.append('be_kill')

	def joined_before_dead(env):
		sleep(0.1)
		env.visitor.append('joined_before_dead')

	def joined_after_dead(env):
		env.visitor.append('joined_after_dead')

	def join_1(env):
		co1 = coroutine.spawn(partial(be_kill, env))
		co2 = coroutine.spawn(partial(joined_after_dead, env))
		co3 = coroutine.spawn(partial(joined_before_dead, env))
		sleep(0.05)
		if co2.dead and env.visitor == ['joined_after_dead']:
			coroutine.kill(co1)
			coroutine.join((co1, co2, co3))
			if co1.dead and co2.dead and co3.dead and env.visitor == ['joined_after_dead', 'joined_before_dead']:
				env.success()
			else:
				env.fail()
		else:
			env.fail()

	run_in_co(join_1, 1)

def test_exception_1():
	def excep():
		sleep(0.1)
		raise ValueError

	def excep1():
		raise ValueError

	def run_1(env):
		co1 = coroutine.spawn(excep)
		co2 = coroutine.run(excep)
		co3 = coroutine.spawn(excep1)
		co4 = coroutine.run(excep1)
		coroutine.join((co1, co2, co3, co4))
		if co1.dead and co2.dead:
			env.success()
		else:
			env.fail()
	run_in_co(run_1, 1)

def test_exception_2():
	def excep():
		raise ValueError

	def run_1(env):
		co1 = coroutine.spawn(excep)
		coroutine.kill(co1)
		if co1.dead:
			env.success()
		else:
			env.fail('co1 not dead')

	def run_2(env):
		co1 = coroutine.run(excep)
		coroutine.kill(co1)
		if co1.dead:
			env.success()
		else:
			env.fail('co1 not dead')

	run_in_co(run_1, 1)
	run_in_co(run_2, 1)

if __name__ == '__main__':
	pass