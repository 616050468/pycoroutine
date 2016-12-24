# -*- coding:utf-8 -*-

import GreenletMgr
from Promise import Promise

use_greenlet = True

if use_greenlet:
	run = GreenletMgr.run_coroutine
	spawn = GreenletMgr.spawn
	kill = GreenletMgr.kill
	join = GreenletMgr.join
	sleep = GreenletMgr.sleep
	Timer = GreenletMgr.Timer
	loop = GreenletMgr.instance().loop
	update = GreenletMgr.instance().update
	Waiter = GreenletMgr.Waiter


class TimeOutWaiter(object):
	def __init__(self, default=None, expired=10):
		self.waiter = Waiter()
		self.p = Promise()
		self.timeout_cb = None
		self.timer_id = None
		self.expired = expired
		self.default = default

	def get(self):
		if self.p.is_pending():
			self.timer_id = Timer.addTimer(self.expired, self._timeout)
			self.p.done(self._switchback, self._switchback)
			return self.waiter.get()
		else:
			return self.p.value()

	def switch(self, *args):
		if self.timer_id is not None:
			Timer.cancelTimer(self.timer_id)
			self.timer_id = None
		self.p.resolve(args)

	def _switchback(self, value):
		self.waiter.switch(value)

	def _timeout(self):
		if self.timeout_cb is not None:
			self.timeout_cb()
		self.p.reject(self.default)

### 提供一个测试运行的环境
running = True

def _loop_empty():
	return GreenletMgr.instance().empty()

def test_stop():
	global running
	running = False

def test_run(fps, main):
	import time
	global running
	running = True
	frameTime = 1.0 / fps

	lastTickTime = 0.0
	accTime = 0.0

	GreenletMgr.init()
	main()

	while True:
		GreenletMgr.instance().loop()

		currentTime = time.time()
		accTime += currentTime - lastTickTime

		if accTime > 0.5:
			accTime = 0.5

		while accTime >= frameTime:
			accTime -= frameTime
			GreenletMgr.instance().update(currentTime)

		lastTickTime = currentTime

		if not running and _loop_empty():
			break