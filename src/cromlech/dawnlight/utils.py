# -*- coding: utf-8 -*-

from urllib import unquote

from cromlech.browser.interfaces import IView
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


def safe_path(path):
    path = unquote(path)
    if not isinstance(path, unicode):
        return unicode(path, 'utf-8')
    return path


def query_view(request, obj, name=""):
    return queryMultiAdapter((obj, request), IView, name=name)


def renderer_locator(func):
    """Can be used as a decorator on the `query_view` function.
    It provides a way to relate the looked up renderer with its lookup
    context.
    """
    def locate_renderer(request, obj, name=""):
        renderer = func(request, obj, name=name)
        if renderer is not None:
            if not ILocation.providedBy(renderer):
                renderer = LocationProxy(renderer)
            locate(renderer, name=name, parent=obj)
        return renderer
    return locate_renderer


def renderer_protector(func):
    """Can be used as a decorator on the `query_http_renderer` function.
    It provides a way to wrap the looked up renderer in a security
    proxy, securing the component accesses.
    """
    def protect_renderer(request, obj, name=""):
        renderer = func(request, obj, name=name)
        if renderer is not None:
            return ProxyFactory(renderer)
        return renderer
    return protect_renderer
