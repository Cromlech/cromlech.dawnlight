# -*- coding: utf-8 -*-

import dawnlight
import grokcore.component as grok
from cromlech.browser.interfaces import IHTTPRenderer
from cromlech.dawnlight import IDawnlightApplication, ModelLookup, ViewLookup
from cromlech.io.interfaces import IPublisher, IRequest, IResponse
from zope.component import queryMultiAdapter
from zope.interface import Interface
from zope.component import getSiteManager

shortcuts = {
    '@@': dawnlight.VIEW,
    }

base_model_lookup = ModelLookup()
base_view_lookup = ViewLookup()


class PublicationUncomplete(Exception):
    pass


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

        model, crumbs = self.model_lookup(self.request, root, stack)
        if not IResponse.providedBy(model):
            view = self.view_lookup(self.request, model, crumbs)
            if view is None:
                raise PublicationUncomplete(
                    'No rendering components for %r' % model)
            return IResponse(view)
        return result


@grok.adapter(IRequest, IDawnlightApplication)
@grok.implementer(IPublisher)
def dawnlight_publisher(request, application):
    return DawnlightPublisher(
        request, application, base_model_lookup, base_view_lookup)


@grok.adapter(IHTTPRenderer)
@grok.implementer(IResponse)
def publish_http_renderer(renderer):
    return renderer()
