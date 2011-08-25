# -*- coding: utf-8 -*-

import dawnlight
import grokcore.component as grok
from cromlech.browser.interfaces import IHTTPRenderer
from cromlech.dawnlight import IDawnlightApplication, ModelLookup, ViewLookup
from cromlech.io.interfaces import IPublisher, IRequest, IResponse
from zope.component import queryMultiAdapter
from zope.interface import Interface, implements

shortcuts = {
    '@@': dawnlight.VIEW,
    }

base_model_lookup = ModelLookup()
base_view_lookup = ViewLookup()


class PublicationUncomplete(Exception):
    pass


class PublicationError(RuntimeError):
    """An exception wrapper.
    """
    def __init__(self, origin):
        Exception.__init__(self, origin.message)
        self.origin = origin


class DawnlightPublisher(object):
    """A publisher using model and view lookup components.
    """

    def __init__(self, request, app,
                 model_lookup=base_model_lookup, view_lookup=base_view_lookup):
        self.app = app
        self.request = request
        self.model_lookup = model_lookup
        self.view_lookup = view_lookup

    def base_path(self, path):
        if path.startswith(self.request.script_name):
            return path[len(self.request.script_name):]
        return path

    def publish(self, root, handle_errors=True):
        path = self.base_path(self.request.path)
        stack = dawnlight.parse_path(path, shortcuts)

        try:
            result, crumbs = self.model_lookup(self.request, root, stack)
            if not IResponse.providedBy(result):
                if crumbs:
                    result = self.view_lookup(self.request, result, crumbs)
                else:
                    result = queryMultiAdapter(
                        (self, self.request, result), IHTTPRenderer)
                    if result is None:
                        raise PublicationUncomplete
                return IResponse(result)
            return result
        except Exception as origin:
            raise PublicationError(origin)


@grok.adapter(IRequest, IDawnlightApplication)
@grok.implementer(IPublisher)
def dawnlight_publisher(request, application):
    return DawnlightPublisher(
        request, application, base_model_lookup, base_view_lookup)


@grok.adapter(IHTTPRenderer)
@grok.implementer(IResponse)
def publish_http_renderer(renderer):
    return renderer()


@grok.adapter(DawnlightPublisher, IRequest, Interface)
@grok.implementer(IHTTPRenderer)
def default_http_renderer(publisher, request, obj):
    return publisher.view_lookup(request, obj, [])
