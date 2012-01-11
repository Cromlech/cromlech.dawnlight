# -*- coding: utf-8 -*-

from cromlech.browser.interfaces import IHTTPRenderer
from zope.component import queryMultiAdapter
from zope.location import ILocation, LocationProxy, locate

try:
    from zope.security.proxy import ProxyFactory
except ImportError:
    def ProxyFactory(obj):
        """A replacement that raises an error.
        """
        raise NotImplementedError(
            'No security factory as been registered. '
            'Unable to protect %r. Please see `zope.security` '
            'for more information regarding security proxies.')


def query_http_renderer(request, obj, name=""):
    return queryMultiAdapter((obj, request), IHTTPRenderer, name=name)


def renderer_locator(func):
    """Can be used as a decorator on the `query_http_renderer` function.
    It provides a way to relate the looked up renderer with its lookup
    context.
    """
    def locate_renderer(request, obj, name=""):
        renderer = func(request, obj, name)
        if renderer is not None:
            if not ILocation.providedBy(renderer):
                renderer = LocationProxy(renderer)
            locate(renderer, name=name, parent=obj)
        return renderer
    return locate_renderer


def renderer_protector(func):
    """Can be used as a decorator on the `query_http_renderer` function.
    It provides a way to wrap the looked up renderer in a security
    proxy, security the component accesses.
    """
    def protect_renderer(request, obj, name=""):
        renderer = func(request, obj, name)
        if renderer is not None:
            return ProxyFactory(renderer)
        return renderer
    return protect_renderer
