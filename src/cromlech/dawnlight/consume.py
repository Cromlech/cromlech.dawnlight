# -*- coding: utf-8 -*-

import grokcore.component as grok
from dawnlight import DEFAULT
from dawnlight.interfaces import IConsumer
from cromlech.browser.interfaces import ITraverser
from zope.interface import Interface
from zope.component import queryMultiAdapter


_marker = object()


def traverse(consumer, request, obj, stack):
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
        if ns == DEFAULT and not name.startswith('_'):
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
        if ns == DEFAULT:
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
