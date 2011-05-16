# -*- coding: utf-8 -*-

import dawnlight
import grokcore.component as grok
from cromlech.browser.interfaces import ITraverser, IHTTPRenderer
from cromlech.dawnlight import publish
from dawnlight.interfaces import IConsumer
from cromlech.io.interfaces import IPublisher, IRequest
from zope.component import queryMultiAdapter
from zope.interface import Interface


class ModelLookup(dawnlight.ModelLookup):
    """used by dawnlight to traverse objects"""

    def __init__(self):
        pass

    def register(self, class_or_interface, consumer):
        """not needed consumers will be declared as subscribers for a context
        implementing IConsumer
        """
        raise NotImplementedError()

    def __call__(self, path, obj, request):
        """traversing : action is delegated to consumer"""
        stack = dawnlight.parse_path(path)
        return self.resolve(stack, obj, request)

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
        return queryMultiAdapter((obj, request), IHTTPRenderer, name=name)



base_model_lookup = ModelLookup()
base_view_lookup = ViewLookup()

@grok.adapter(IRequest, IDawnlightApplication)
@grok.implementer(IPublisher)
def publisher(request, application):
    return DawnlightPublisher(
        request, application, base_model_lookup, base_view_lookup)


class DawnlightPublisher(object):
    """The publisher using model and view lookup

    same role as Application in dawnlight
    """

    def __init__(self, request, app,
                 model_lookup=base_model_lookup, view_lookup=base_view_lookup):
        self.app = app
        self.request = request
        self.model_lookup = model_lookup
        self.view_lookup = view_lookup

    def _root_path(self, path):
        if path.startswith(self.request.script_name):
            return path[len(self.request.script_name):]
        return path

    def publish(self, root, handle_errors=True):
        """Traverse and call view.
        """
        path = self._root_path(self.request.path)
        model, unconsumed = self.model_lookup(path, root, self.request)
        view = self.view_lookup(self.request, model, unconsumed)
        return view()


_marker = object()


def traverse(consumer, stack, obj, request):
    """Furnish the base consumer __call__ method delegating
    the resolution to the _resolve method.
    """
    ns, name = stack.pop()
    next_obj = consumer._resolve(obj, ns, name, request)
    if next_obj is None:
        stack.append((ns, name))
        return False, obj, stack
    return True, next_obj, stack


class AttributeConsumer(grok.Subscription):
    """Default path consumer for model lookup, traversing objects
    using their attributes

    It does not traverse on reserved / private attributes
    """
    grok.implements(IConsumer)
    grok.context(Interface)
    grok.order(1100)  # intend to be first !

    __call__ = traverse

    def _resolve(self, obj, ns, name, request):
        if ns == u'default':
            if not name.startswith('_'):
                attr = getattr(obj, name, _marker)
                if attr is not _marker:
                    return attr
        return None


class ItemConsumer(grok.Subscription):
    """Default path consumer for model lookup, traversing objects
    using their attributes or, as second choice, contained items.
    """
    grok.implements(IConsumer)
    grok.context(Interface)
    grok.order(1000)  # intend to be second !

    __call__ = traverse

    def _resolve(self, obj, ns, name, request):
        if ns == u'default':
            if hasattr(obj, '__getitem__'):
                try:
                    return obj[name]
                except (KeyError, TypeError):
                    pass
        return None


class TraverserConsumer(grok.Subscription):
    """Consumer for model lookup, using traversing by adaptation
    to ITraverser.
    """
    grok.implements(IConsumer)
    grok.context(Interface)
    grok.order(900)  # intend to be third !

    __call__ = traverse

    def _resolve(self, obj, ns, name, request):
        traverser = queryMultiAdapter((obj, request), ITraverser, name=ns)
        if traverser:
            return traverser.traverse(ns, name)
        return None
