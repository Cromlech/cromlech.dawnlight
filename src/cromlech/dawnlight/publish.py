# -*- coding: utf-8 -*-

import traceback
import sys

import dawnlight
import grokcore.component as grok

from cromlech.browser import IRequest, IResponse
from cromlech.browser import IPublisher, IView, IResponseFactory
from cromlech.dawnlight import IDawnlightApplication
from cromlech.dawnlight.lookup import ModelLookup, ViewLookup
from cromlech.dawnlight.utils import safe_path
from zope.component import queryMultiAdapter, queryAdapter
from zope.component.interfaces import ComponentLookupError
from zope.location import LocationProxy, locate, ILocation
from zope.proxy import removeAllProxies


shortcuts = {
    '@@': dawnlight.VIEW,
    }

base_model_lookup = ModelLookup()
base_view_lookup = ViewLookup()


def safeguard(func):
    def handle_errors(component, root, handle_errors=True):
        if handle_errors is True:
            try:
                response = func(component, root, handle_errors=handle_errors)
            except Exception, e:
                if not ILocation.providedBy(e):
                    # Make sure it's properly located.
                    e = LocationProxy(e)
                    locate(e, root, 'error')
                response = queryMultiAdapter(
                    (component.request, e), IView)
                if response is None:
                    raise
            return response
        return func(component, root, handle_errors=handle_errors)
    return handle_errors


class PublicationError(Exception):
    pass


class PublicationErrorBubble(PublicationError):
    """Bubbling up error.
    """
    def __init__(self, wrapped, tb_info):
        self.wrapped = wrapped
        PublicationError.__init__(
            self,
            'Publication error: %s\nOriginal traceback:\n%s' %
            (str(wrapped),
             '    '.join(traceback.format_exception(*tb_info))))


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
        script_name = unicode(self.request.script_name, 'utf-8')
        if path.startswith(script_name):
            return path[len(script_name):]
        return path

    @safeguard
    def publish(self, root, **args):
        path = self.base_path(safe_path(self.request.path))
        stack = dawnlight.parse_path(path, shortcuts)

        model, crumbs = self.model_lookup(self.request, root, stack)
        if IResponse.providedBy(model):
            # The found object can be returned safely.
            return model
        if IResponseFactory.providedBy(model):
            return model()

        # The model needs an renderer
        component = self.view_lookup(self.request, model, crumbs)
        if component is None:
            raise PublicationError('%r can not be rendered.' % model)

        # This renderer needs to be resolved into an IResponse
        factory = IResponseFactory(component)
        return factory()


@grok.adapter(IRequest, IDawnlightApplication)
@grok.implementer(IPublisher)
def dawnlight_publisher(request, application):
    return DawnlightPublisher(
        request, application, base_model_lookup, base_view_lookup)


@grok.adapter(IRequest, Exception)
@grok.implementer(IResponseFactory)
def exception_view(request, exception):
    view = queryMultiAdapter((exception, request), IView)
    if view is not None:
        # Make sure it's properly located.
        located = LocationProxy(view)
        locate(view, exception, name='exception')
        return IResponseFactory(view)
    return None
