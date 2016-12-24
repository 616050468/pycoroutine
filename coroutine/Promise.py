# -*- coding:utf-8 -*-
# @Author: gzliwenfeng<gzliwenfeng@corp.netease.com>
# @Description: Promise/A+

import sys
from functools import partial

class Promise(object):
	PENDING = 0
	FULFILLED = 1
	REJECTED = 2

	late_updates = []

	on_traceback = None

	def __init__(self):
		self._value = None
		self._status = Promise.PENDING
		self._handlers = []

	@staticmethod
	def add_late_update(func):
		Promise.late_updates.append(func)

	@staticmethod
	def update():
		on_traceback = Promise.on_traceback
		while len(Promise.late_updates) > 0:
			updates = Promise.late_updates
			Promise.late_updates = []
			for func in updates:
				try:
					func()
				except:
					if on_traceback:
						exc_info = sys.exc_info()
						on_traceback(exc_info[0], exc_info[1], exc_info[2])

	def value(self):
		return self._value

	def is_pending(self):
		return self._status == Promise.PENDING

	def is_fulfilled(self):
		return self._status == Promise.FULFILLED

	def is_rejected(self):
		return self._status == Promise.REJECTED

	def resolve(self, value):
		if self._status != Promise.PENDING:
			return
		if self is value:
			return self.reject(ValueError('value should not refer to the same Promise'))

		if isinstance(value, Promise):
			try:
				value.done(self.resolve, self.reject)
			except Exception as e:
				e.exc_info = sys.exc_info()
				self.reject(e)
		else:
			self._status = Promise.FULFILLED
			self._value = value
			self._notify_links()

	def reject(self, value):
		if self._status != Promise.PENDING:
			return
		self._status = Promise.REJECTED
		self._value = value
		self._notify_links()

	def then(self, onFulfilled=None, onRejected=None):
		p = Promise()

		def _onFulfilled(value):
			if onFulfilled:
				try:
					p.resolve(onFulfilled(value))
				except Exception as e:
					e.exc_info = sys.exc_info()
					p.reject(e)
			else:
				p.resolve(value)

		def _onRejected(value):
			if onRejected:
				try:
					p.resolve(onRejected(value))
				except Exception as e:
					e.exc_info = sys.exc_info()
					p.reject(e)
			else:
				p.reject(value)

		self.done(_onFulfilled, _onRejected)
		return p

	def done(self, onFulfilled, onRejected):
		if self._status == Promise.FULFILLED:
			if onFulfilled: Promise.add_late_update(partial(onFulfilled, self._value))
		elif self._status == Promise.REJECTED:
			if onRejected: Promise.add_late_update(partial(onRejected, self._value))
		else:
			self._handlers.append((onFulfilled, onRejected))

	def _notify_links(self):
		#print '_notify_links', self._status, len(self._handlers), type(self._value)
		status = self._status
		if status == Promise.PENDING:
			return
		handlers = self._handlers
		self._handlers = []
		value = self._value
		for handler in handlers:
			if status == Promise.FULFILLED:
				fun = handler[0]
			else:
				fun = handler[1]
			if fun: Promise.add_late_update(partial(fun, value))

