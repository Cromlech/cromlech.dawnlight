# -*- coding: utf-8 -*-

import zope.component
import grokcore.component

from zope.interface import Interface
from zope.publisher.defaultview import getDefaultViewName
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import (
    IBrowserPublisher, IBrowserRequest)


class SimpleComponentTraverser(grokcore.component.MultiAdapter):
    grokcore.component.provides(IBrowserPublisher)
    grokcore.component.adapts(Interface, IBrowserRequest)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def browserDefault(self, request):
        ob = self.context
        view_name = getDefaultViewName(ob, request)
        return ob, (view_name,)

    def publishTraverse(self, request, name):
        ob = self.context
        view = zope.component.queryMultiAdapter((ob, request), name=name)
        if view is None:
            raise NotFound(ob, name)
        return view
