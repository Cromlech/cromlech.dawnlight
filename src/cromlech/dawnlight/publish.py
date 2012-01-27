# -*- coding: utf-8 -*-

import dawnlight
import grokcore.component as grok

from cromlech.browser import IHTTPRenderer, IHTTPRequest, IHTTPResponse
from cromlech.dawnlight import IDawnlightApplication
from cromlech.dawnlight.lookup import ModelLookup
from cromlech.dawnlight.utils import query_http_renderer, safe_path
from cromlech.io.interfaces import IPublisher
from zope.component import queryMultiAdapter
from zope.component.interfaces import ComponentLookupError
from zope.location import LocationProxy, locate
from zope.proxy import removeAllProxies


shortcuts = {
    '@@': dawnlight.VIEW,
    }

base_model_lookup = ModelLookup()
base_view_lookup = dawnlight.ViewLookup(query_http_renderer)


def safeguard(func):
    def handle_errors(component, root, handle_errors=True):
        if handle_errors is True:
            try:
                response = func(component, root, handle_errors=handle_errors)
            except Exception, e:
                response = queryMultiAdapter(
                    (component.request, e), IHTTPResponse)
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
    def __init__(self, wrapped):
        self.wrapped = wrapped
        PublicationError.__init__(
            self, 'Publication error: %s' % str(wrapped))

    def __str__(self):
        return str(self.wrapped)

    def __repr__(self):
        return repr(self.wrapped)


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
        if IHTTPResponse.providedBy(model):
            # The found object can be returned safely.
            return model

        # The model needs an renderer
        view = self.view_lookup(self.request, model, crumbs)
        if view is None:
            raise PublicationError('%r can not be rendered.' % model)
        return IHTTPResponse(view)


@grok.adapter(IHTTPRequest, IDawnlightApplication)
@grok.implementer(IPublisher)
def dawnlight_publisher(request, application):
    return DawnlightPublisher(
        request, application, base_model_lookup, base_view_lookup)


@grok.adapter(IHTTPRequest, Exception)
@grok.implementer(IHTTPResponse)
def exception_view(request, exception):
    view = queryMultiAdapter((exception, request), IHTTPRenderer)
    if view is not None:
        return view()
    return None


@grok.adapter(IHTTPRenderer)
@grok.implementer(IHTTPResponse)
def publish_http_renderer(renderer):
    """Adaptation has a tendency to shadow some kind of errors.
    More precisely, non-handled ComponentLookupError can be seen
    as an adaptation failure while they originate from deeper in the
    code. That's why we cover that basis.
    """
    try:
        return renderer()
    except ComponentLookupError as e:

        # The render is likely to be wrapped in a security proxy.
        # We get rid of that proxy to access the component freely.
        view = removeAllProxies(renderer)

        # Locating the error allows us to know more about the failure
        # context. We use the context of the view, as we might have
        # removed the location proxy of the view.
        error = LocationProxy(e)
        locate(error, view.context, 'error')

        # Finally, we wrap the error in a 'bubble', keeping its traceback
        # and we raise the bubble. A bubble is an error that is internal
        # to the publisher. The publisher will then decide what to do with
        # that wrapped error.
        raise PublicationErrorBubble(error)
