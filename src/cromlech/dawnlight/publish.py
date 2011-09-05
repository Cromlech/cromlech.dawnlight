# -*- coding: utf-8 -*-

import dawnlight
import grokcore.component as grok
from cromlech.browser.interfaces import IHTTPRenderer
from cromlech.dawnlight import IDawnlightApplication, ModelLookup, ViewLookup
from cromlech.io.interfaces import IPublisher, IRequest, IResponse
from zope.component import queryMultiAdapter
from zope.component.interfaces import ComponentLookupError
from zope.location import LocationProxy, locate

shortcuts = {
    '@@': dawnlight.VIEW,
    }

base_model_lookup = ModelLookup()
base_view_lookup = ViewLookup()


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
        if path.startswith(self.request.script_name):
            return path[len(self.request.script_name):]
        return path

    def publish(self, root, handle_errors=True):
        path = self.base_path(self.request.path)
        stack = dawnlight.parse_path(path, shortcuts)

        model, crumbs = self.model_lookup(self.request, root, stack)
        if IResponse.providedBy(model):
            # The found object can be returned safely.
            return model

        # The model needs an renderer
        view = self.view_lookup(self.request, model, crumbs)
        if view is None:
            raise PublicationError('%r can not be rendered.' % model)
        return IResponse(view)


@grok.adapter(IRequest, IDawnlightApplication)
@grok.implementer(IPublisher)
def dawnlight_publisher(request, application):
    return DawnlightPublisher(
        request, application, base_model_lookup, base_view_lookup)


@grok.adapter(IHTTPRenderer)
@grok.implementer(IResponse)
def publish_http_renderer(renderer):
    try:
        return renderer()
    except ComponentLookupError as e:
        error = LocationProxy(e)
        locate(error, renderer.context, 'error')
        raise PublicationErrorBubble(error)
    except Exception as e:
        error = LocationProxy(e)
        locate(error, renderer.context, 'error')
        result = queryMultiAdapter((error, renderer.request), IHTTPRenderer)
        if result is not None:
            try:
                return result()
            except Exception as e2:
                # We failed to fail.
                # Let's return something sensible.
                raise PublicationError(
                    'A publication error (%r) happened, while trying to '
                    'render the error (%r)' % (e2, e))
        else:
            raise
