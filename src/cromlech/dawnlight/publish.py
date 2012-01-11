# -*- coding: utf-8 -*-
from urllib import unquote

import dawnlight
import grokcore.component as grok
from cromlech.browser import IHTTPRenderer, IHTTPRequest, IHTTPResponse
from cromlech.dawnlight import IDawnlightApplication
from cromlech.dawnlight.lookup import ViewLookup, ModelLookup
from cromlech.dawnlight.utils import query_http_renderer
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

    def publish(self, root, handle_errors=True):
        path = unicode(unquote(self.request.path), 'utf-8')
        path = self.base_path(path)
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


@grok.adapter(IHTTPRenderer)
@grok.implementer(IHTTPResponse)
def publish_http_renderer(renderer):
    try:
        return renderer()
    except ComponentLookupError as e:
        error = LocationProxy(e)
        view = removeAllProxies(renderer)
        locate(error, view.context, 'error')
        raise PublicationErrorBubble(error)
    except Exception as e:
        error = LocationProxy(e)
        view = removeAllProxies(renderer)
        locate(error, view.context, 'error')
        result = queryMultiAdapter((error, view.request), IHTTPRenderer)
        if result is not None:
            try:
                return result()
            except Exception as e2:
                # We failed to fail.
                # Let's return something sensible.
                raise PublicationError(
                    'A publication error (%r) happened, while trying to '
                    'render the error (%r)' % (e2, e))
        raise
