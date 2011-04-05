# -*- coding: utf-8 -*-

import dawnlight
import grokcore.component as grok
from cromlech.dawnlight import IDawnlightApplication
from dawnlight.interfaces import IConsumer
from cromlech.io.interfaces import IPublisher, IRequest
from zope.component import queryAdapter, queryMultiAdapter
from zope.interface import implements, Interface


class ModelLookup(dawnlight.ModelLookup):
    """used by dawnlight to traverse objects"""

    def __init__(self):
        pass
    
    def register(self, class_or_interface, consumer):
        """not needed consumers will be declared as subscribers for a context 
        implementing IConsumer
        """
        raise NotImplementedError()

    def __call__(self, path, obj):
        """traversing : action is delegated to consumer"""
        stack = dawnlight.parse_path(path)
        return self.resolve(stack, obj)

    def lookup(self, obj):
        """search for possible pach consumers
        """
        return grok.querySubscriptions(obj, IConsumer)


class ViewLookup(dawnlight.ViewLookup):
    """Used by dawnlight on last object at end of traversal to find view"""

    default_view_name = u'index'

    def __init__(self):
        pass

    def view_lookup_func(self, request, obj, name):
        """look up view named name on obj for request"""
        return queryMultiAdapter((obj, request), name=name)


class DawnlightPublisher(grok.MultiAdapter):
    """The publisher using model and view lookup
    
    same role as Application in dawnlight
    
    """
    
    grok.implements(IPublisher)
    grok.adapts(IRequest, IDawnlightApplication)

    model_lookup = ModelLookup()
    view_lookup = ViewLookup()

    def __init__(self, request, app):
        self.app = app
        self.request = request

    def _root_path(self, path):
        if path.startswith(self.request.script_name):
            return path[len(self.request.script_name):]
        return path

    def publish(self, root, handle_errors=True):
        """Traverse and call view"""
        path = self._root_path(self.request.path)
        model, unconsumed = self.model_lookup(path, root)
        view = self.view_lookup(self.request, model, unconsumed)
        return view()


_marker = object()

class DefaultConsumer(grok.Subscription):
    """Default path consumer for model lookup, traversing objects
    using their attributes or, as second choice, contained items
    """
    grok.implements(IConsumer)
    grok.context(Interface)
    grok.order(1000) # intend to be first !

    def _resolve(self, obj, ns, name):
        if ns != u'default':
            return None

        attr = getattr(obj, name, _marker)
        if attr is not _marker:
            return attr
        if hasattr(obj, '__getitem__'):
            try:
                return obj[name]
            except (KeyError, TypeError):
                pass
        return None

    def __call__(self, stack, obj):
        ns, name = stack.pop()
        next_obj = self._resolve(obj, ns, name)
        if next_obj is None:
            stack.append((ns, name))
            return False, obj, stack
        return True, next_obj, stack
