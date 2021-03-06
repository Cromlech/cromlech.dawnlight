# -*- coding: utf-8 -*-

import sys
from crom import ComponentLookupError
from cromlech.browser.interfaces import IView, IResponseFactory
from zope.location import ILocation, LocationProxy, locate
from .interfaces import ITracebackAware


def query_view(request, obj, name=""):
    return IView(obj, request, name=name, default=None)


def view_locator(func):
    """Can be used as a decorator on the `query_view` function.
    It provides a way to relate the looked up view with its lookup
    context.
    """
    def locate_view(request, obj, name=""):
        view = func(request, obj, name=name)
        if view is not None:
            if not ILocation.providedBy(view):
                view = LocationProxy(view)
            locate(view, name=name, parent=obj)
        return view
    return locate_view


def safeguard(func):
    def publish_handle_errors(publisher, request, root, handle_errors=True):
        if handle_errors is True:
            try:
                response = func(publisher, request, root, handle_errors)
            except Exception as e:
                if not ILocation.providedBy(e):
                    # Make sure it's properly located.
                    error = LocationProxy(e)
                    locate(error, root, 'error')
                try:
                    factory = IResponseFactory(request, error)
                    if ITracebackAware.providedBy(factory):
                        exc_info = sys.exc_info()
                        factory.set_exc_info(exc_info)
                    response = factory()
                except ComponentLookupError:
                    raise e
            return response
        return func(publisher, request, root, handle_errors=handle_errors)
    return publish_handle_errors
