# -*- coding: utf-8 -*-
class ViewRequest(object):
	Nothing = 0
	Refresh = 1 << 0
	PointerHeldEventsRequest = 1 << 1
	PointerHeldEventsCancel = 1 << 2
	Exit = 1 << 4
