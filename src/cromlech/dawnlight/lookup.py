# -*- coding: utf-8 -*-

from cromlech.browser import IView
from .utils import query_view
from .registry import dawnlight_components
from dawnlight import DEFAULT, VIEW, ResolveError
from dawnlight import ModelLookup as BaseModelLookup
from dawnlight.interfaces import IConsumer, ILookupComponent
from zope.interface import implementer


class ModelLookup(BaseModelLookup):

    def __init__(self):
        pass

    def register(self, class_or_interface, consumer):
        """Consumers are intended to be subscription adapters.
        """
        raise NotImplementedError(u"Use the global registry.")

    def lookup(self, obj):
        """We use IConsumer registered in the global registry as
        subscription adapters.
        """
        return IConsumer.subscription(
            obj, lookup=dawnlight_components, subscribe=True)


@implementer(ILookupComponent)
class ViewLookup(object):
    """Looks up a view using a given method.
    """

    def __init__(self, lookup=query_view, default_name=u'index'):
        self.lookup = lookup
        self.default_name = default_name

    def __call__(self, request, obj, stack):
        """Resolves a view.
        """
        default_fallback = False
        unconsumed_amount = len(stack)
        if unconsumed_amount == 0:
            default_fallback = True
            ns, name = VIEW, self.default_name
        elif unconsumed_amount == 1:
            ns, name = stack[0]
        else:
            raise ResolveError(
                "Can't resolve view: stack is not fully consumed.")

        if ns not in (DEFAULT, VIEW):
            raise ResolveError(
                "Can't resolve view: namespace %r is not supported." % ns)

        # If this is the last node AND if it's a view, we return it.
        if default_fallback and IView.providedBy(obj):
            return obj

        # Else, we need to resolve the model into a view.
        view = self.lookup(request, obj, name)
        if view is None:
            if default_fallback:
                raise ResolveError(
                    "Can't resolve view: no default view on %r." % obj)
            else:
                if ns == VIEW:
                    raise ResolveError(
                        "Can't resolve view: no view `%s` on %r." % (name, obj))
                raise ResolveError(
                    "%r is neither a view nor a model." % name)
        return view
