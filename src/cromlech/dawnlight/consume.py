# -*- coding: utf-8 -*-

import crom

from .registry import dawnlight_components
from .directives import traversable
from .publish import safe_unicode

from dawnlight import DEFAULT
from dawnlight.interfaces import IConsumer
from cromlech.browser import ITraverser
from zope.interface import Interface
from zope.interface.interfaces import ComponentLookupError


_marker = object()


def traverse(consumer, request, obj, stack):
    """Furnish the base consumer __call__ method delegating
    the resolution to the _resolve method.
    """
    ns, name = stack.popleft()
    next_obj = consumer._resolve(obj, ns, name, request)
    if next_obj is None:
        # Nothing was found, we restore the stack.
        stack.appendleft((ns, name))
        return False, obj, stack
    return True, next_obj, stack


@crom.subscription
@crom.sources(Interface)
@crom.target(IConsumer)
@crom.order(1100)
@crom.registry(dawnlight_components)
class AttributeConsumer(object):
    """Default path consumer for model lookup, traversing objects
    using their attributes that are declared traversable through
    traversable directive
    """
    __call__ = traverse

    def __init__(self, context):
        self.context = context

    def _resolve(self, obj, ns, name, request):
        name = safe_unicode(name, 'utf-8')
        traversables_attrs = traversable.get(self.context)
        if traversables_attrs and ns == DEFAULT and name in traversables_attrs:
            attr = getattr(obj, name, _marker)
            if attr is not _marker:
                return attr
        return None


@crom.subscription
@crom.sources(Interface)
@crom.target(IConsumer)
@crom.order(1000)
@crom.registry(dawnlight_components)
class ItemConsumer(object):
    """Default path consumer for model lookup, traversing objects
    using their attributes or, as second choice, contained items.
    """
    __call__ = traverse

    def __init__(self, context):
        self.context = context

    def _resolve(self, obj, ns, name, request):        
        if ns == DEFAULT:
            if hasattr(obj, '__getitem__'):
                try:
                    return obj[name]
                except (KeyError, TypeError):
                    pass
        return None


@crom.subscription
@crom.sources(Interface)
@crom.target(IConsumer)
@crom.order(900)
@crom.registry(dawnlight_components)
class TraverserConsumer(object):
    """Consumer for model lookup, using traversing by adaptation
    to ITraverser.
    """
    __call__ = traverse

    def __init__(self, context):
        self.context = context

    def _resolve(self, obj, ns, name, request):
        try:
            traverser = ITraverser(obj, request, name=ns)
            if traverser:
                return traverser.traverse(ns, name)
        except ComponentLookupError:
            pass
        return None
