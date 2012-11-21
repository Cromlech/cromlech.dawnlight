# -*- coding: utf-8 -*-

import crom
from dawnlight import DEFAULT
from dawnlight.interfaces import IConsumer
from cromlech.browser.interfaces import ITraverser
from cromlech.dawnlight.directives import traversable
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


@crom.adapter
@crom.sources(Interface)
@crom.target(IConsumer)
@crom.implements(ITarget)
@crom.order(1100)
class AttributeConsumer(object):
    """Default path consumer for model lookup, traversing objects
    using their attributes that are declared traversable through
    traversable directive
    """
    __call__ = traverse

    def __init__(self, context):
        self.context = context

    def _resolve(self, obj, ns, name, request):
        name = name.encode('utf-8') if isinstance(name, unicode) else name
        traversables_attrs = traversable.bind().get(self.context)
        if ns == DEFAULT and name in traversables_attrs:
            attr = getattr(obj, name, _marker)
            if attr is not _marker:
                return attr
        return None


@crom.adapter
@crom.sources(Interface)
@crom.target(IConsumer)
@crom.implements(ITarget)
@crom.order(1000)
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


@crom.adapter
@crom.sources(Interface)
@crom.target(IConsumer)
@crom.implements(ITarget)
@crom.order(900)
class TraverserConsumer(object):
    """Consumer for model lookup, using traversing by adaptation
    to ITraverser.
    """
    __call__ = traverse

    def __init__(self, context):
        self.context = context

    def _resolve(self, obj, ns, name, request):
        lookup 
        traverser = queryMultiAdapter((obj, request), ITraverser, name=ns)
        if traverser:
            return traverser.traverse(ns, name)
        return None
