# -*- coding: utf-8 -*-

import sys
import inspect

from urllib import unquote
from cromlech.browser.interfaces import IView, IResponseFactory
from zope.component import queryMultiAdapter
from zope.location import ILocation, LocationProxy, locate


def safe_path(path):
    path = unquote(path)
    if not isinstance(path, unicode):
        return unicode(path, 'utf-8')
    return path


def query_view(request, obj, name=""):
    return queryMultiAdapter((obj, request), IView, name=name)


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
            except Exception, e:
                if not ILocation.providedBy(e):
                    # Make sure it's properly located.
                    e = LocationProxy(e)
                    locate(e, root, 'error')
                factory = queryMultiAdapter((request, e), IResponseFactory)
                if factory is not None:
                    # Error views can get the traceback
                    # This violates the IResponseFactory __call__ contract
                    # Maybe this should be reviewed
                    if 'exc_info' in inspect.getargspec(factory.__call__).args:
                        exc_info = sys.exc_info()
                        response = factory(exc_info=exc_info)
                    else:
                        response = factory()
                else:
                    raise
            return response
        return func(publisher, request, root, handle_errors=handle_errors)
    return publish_handle_errors
