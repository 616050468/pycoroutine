# -*- coding:utf-8 -*-
# @Author: gzliwenfeng<gzliwenfeng@corp.netease.com>
# @Description: 协程管理器
__author__ = 'gzliwenfeng'

import sys
from greenlet import greenlet, getcurrent, GreenletExit
import time
import traceback
from collections import deque
from Promise import Promise
from functools import partial

hub_greenlet = None
CALLBACK_TIMEOUT = 10

def print_tb(typ, val, tb):
	print 'on_traceback, type:%s, value:%s, traceback:%s' % (typ, val, tb)
	print traceback.format_exc()

on_traceback = lambda typ, val, tb: print_tb(typ, val, tb)

def init(traceback_cb=None):
	global hub_greenlet, on_traceback
	hub_greenlet = getcurrent()
	if traceback_cb:
		on_traceback = traceback_cb
		Promise.on_traceback = traceback_cb
	else:
		Promise.on_traceback = on_traceback

class Coroutine(greenlet):
	value = None
	args = ()
	_kwargs = None
	_start = False
	_links = None
	_notifier = None
	def __init__(self, run, *args, **kwargs):
		super(Coroutine, self).__init__(None, hub_greenlet)
		if not callable(run):
			raise TypeError("The run argument or self._run must be callable")
		self._run = run
		if args:
			self.args = args
		if kwargs:
			self._kwargs = kwargs

	@property
	def kwargs(self):
		return self._kwargs or {}

	def start(self):
		if not self._start:
			self._start = True
			GreenletMgr.instance().run_callback(self.switch)

	def rawlink(self, callback):
		if not callable(callback):
			raise TypeError('Expected callable: %r' % (callback, ))
		if self._links is None:
			self._links = deque()
		self._links.append(callback)
		if self.dead and not self._notifier:
			self._notifier = GreenletMgr.instance().run_callback(self._notify_links)

	def _notify_links(self):
		if self._links is None:
			return
		while self._links:
			link = self._links.popleft()
			try:
				link(self)
			except:
				GreenletMgr.instance()._report_error(sys.exc_info())
		self._links = None
		self._notifier = None

	def _report_error(self, exc_info):
		if isinstance(exc_info[1], GreenletExit):
			self._report_result(exc_info[1])
			return
		if not self._notifier:
			self._notifier = GreenletMgr.instance().run_callback(self._notify_links)
		on_traceback(*exc_info)

	def _report_result(self, result):
		self.value = result
		if not self._notifier:
			self._notifier = GreenletMgr.instance().run_callback(self._notify_links)

	def run(self):
		try:
			try:
				result = self._run(*self.args, **self.kwargs)
			except:
				self._report_error(sys.exc_info())
				return
			self._report_result(result)
		finally:
			self.__dict__.pop('_run', None)
			self.__dict__.pop('args', None)
			self.__dict__.pop('kwargs', None)

class _NONE(object):
	"""
	A special object you must never pass to any gevent API.
	Used as a marker object for keyword arguments that cannot have the
	builtin None (because that might be a valid value).
	"""
	__slots__ = ()

	def __repr__(self):
		return '<default value>'

_NONE = _NONE()

class Waiter(object):
	__slots__ = ['greenlet', 'value', '_exception', '_ready']
	def __init__(self):
		self.greenlet = None
		self.value = None
		self._exception = _NONE
		self._ready = False

	def clear(self):
		self.greenlet = None
		self.value = None
		self._exception = _NONE
		self._ready = False

	def get(self):
		if self._ready:
			if self._exception is None:
				return self.value
			else:
				getcurrent().throw(*self._exception)
		else:
			assert self.greenlet is None, 'This Waiter is already used by %r' % (self.greenlet, )
			greenlet = getcurrent()
			self.greenlet = greenlet
			try:
				return greenlet.parent.switch()
			finally:
				self.greenlet = None

	def switch(self, value=None):
		greenlet = self.greenlet
		if greenlet is None:
			self._ready = True
			self.value = value
			self._exception = None
		else:
			assert getcurrent() is hub_greenlet, "Can only use Waiter.switch method from the Hub greenlet"
			switch = greenlet.switch
			try:
				switch(value)
			except:
				on_traceback(*sys.exc_info())

class _MultipleWaiter(Waiter):
	__slots__ = ['_values']
	def __init__(self):
		Waiter.__init__(self)
		self._values = list()

	def switch(self, value):
		self._values.append(value)
		Waiter.switch(self, True)

	def get(self):
		if not self._values:
			Waiter.get(self)
			self.clear()
		return self._values.pop(0)

def iwait(objects):
	count = len(objects)
	waiter = _MultipleWaiter()
	switch = waiter.switch
	try:
		for obj in objects:
			obj.rawlink(switch)
		for _ in xrange(count):
			co = waiter.get()
			waiter.clear()
			yield co
	finally:
		pass

def run_coroutine(fun, *args, **kwargs):
	gr = Coroutine(fun, *args, **kwargs)
	## 先设置父亲为当前协程，等gr执行一次之后返回当前协程，再把gr挂在主协程下面，从而实现马上执行协程
	gr.parent = getcurrent()
	gr.switch()
	if not gr.dead:
		gr.parent = hub_greenlet
	return gr

def spawn(fun, *args, **kwargs):
	gr = Coroutine(fun, *args, **kwargs)
	gr.start()
	return gr

def kill(coroutine, block=True, exception=GreenletExit):
	try:
		if coroutine.dead:
			return True
		current = getcurrent()
		if current is hub_greenlet:
			try:
				coroutine.throw(exception)
				return coroutine.dead
			except:
				return coroutine.dead
		else:
			if block:
				waiter = Waiter()
				GreenletMgr.instance().run_callback(partial(_kill, coroutine, exception, waiter))
				waiter.get()
			else:
				GreenletMgr.instance().run_callback(partial(_kill, coroutine, exception, None))
	except:
		on_traceback(*sys.exc_info())

def _kill(coroutine, exception, waiter):
	## 只能在主协程被调用
	dead = True
	if not coroutine.dead:
		try:
			coroutine.throw(exception)
		except:
			on_traceback(*sys.exc_info())
		dead = coroutine.dead
	if waiter is None:
		return
	waiter.switch(dead)

def join(coroutines):
	"""
	Wait for coroutines to finish
	:param coroutines: A sequence (supporting :func:`len`) of coroutines to wait for.
	:return: A sequence of the coroutines that finished (if any)
	"""
	if len(coroutines) > 0:
		cur = getcurrent()
		assert cur is not hub_greenlet, "Can not use join from the Hub greenlet"
		return list(iwait(coroutines))
	else:
		return ()

def sleep(seconds):
	waiter = Waiter()
	if seconds <= 0:
		waiter = Waiter()
		GreenletMgr.instance().run_callback(waiter.switch)
		waiter.get()
	else:
		Timer.addTimer(seconds, waiter.switch)
		waiter.get()

def instance():
	return GreenletMgr.instance()

class TimerMgr(object):
	'''
	提供一个粗糙的定时器功能
	'''
	_instance = None
	def __init__(self):
		self._tid = 0
		self.timers = {}

	@classmethod
	def instance(cls):
		if cls._instance is None:
			cls._instance = cls()
		return cls._instance

	def addTimer(self, timeout, cb):
		if not callable(cb):
			raise TypeError('timer callback not callable')
		expired = time.time() + timeout
		self._tid += 1
		tid = self._tid
		self.timers[tid] =  (expired, cb)
		return tid

	def cancelTimer(self, tid):
		if self.timers.pop(tid, None) is None:
			return False
		else:
			return True

	def update(self, now):
		timers = self.timers
		cblist = []
		for k, v in timers.iteritems():
			if v[0] > now:
				continue
			cblist.append(k)
		for k in cblist:
			v = timers.pop(k, None)
			if v is None:
				continue
			try:
				v[1]()
			except:
				on_traceback(*sys.exc_info())

	def empty(self):
		if self.timers:
			return False
		return True

Timer = TimerMgr.instance()

class GreenletMgr(object):
	_instance = None
	def __init__(self):
		self._callbacks = []

	@classmethod
	def instance(cls):
		if cls._instance is None:
			cls._instance = cls()
		return cls._instance

	def _report_error(self, exc_info):
		if isinstance(exc_info[1], GreenletExit):
			return
		on_traceback(*exc_info)

	def empty(self):
		if self._callbacks:
			return False
		if not Timer.empty() or len(Promise.late_updates) != 0:
			return False
		return True

	def update(self, now):
		Timer.update(now)

	def loop(self):
		Promise.update()
		callbacks = self._callbacks
		self._callbacks = []
		for cb in callbacks:
			try:
				cb()
			except:
				self._report_error(sys.exc_info())

	def run_callback(self, func):
		self._callbacks.append(func)

