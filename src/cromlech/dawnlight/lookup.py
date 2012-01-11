# -*- coding: utf-8 -*-

import dawnlight
from grokcore.component import querySubscriptions
from cromlech.browser.interfaces import IHTTPRenderer
from dawnlight.interfaces import IConsumer
from zope.component import queryMultiAdapter

try:
    from zope.security.proxy import ProxyFactory
except ImportError:
    class ProxyFactory(object):
        """A replacement that raises an error.
        """
        def __init__(self, obj):
            raise NotImplementedError(
                'No security factory as been registered. '
                'Unable to protect %r. Please see `zope.security` '
                'for more information regarding security proxies.')


def query_http_renderer(request, obj, name=""):
    return queryMultiAdapter((obj, request), IHTTPRenderer, name=name)


def renderer_locator(func):
    def locate_view(request, obj, stack):
        view = func(request, obj, stack)
        if view is not None:
            locate(view, name=name, parent=obj)
        return view
    return locate_view


def renderer_protector(func):
    def protect_view(request, obj, stack):
        view = func(request, obj, stack)
        if view is not None:
            return ProxyFactory(view)
        return view
    return protect_view


class ModelLookup(dawnlight.ModelLookup):

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
        return querySubscriptions(obj, IConsumer)
