# -*- coding: utf-8 -*-

import crom
import dawnlight

from .lookup import ModelLookup, ViewLookup
from .utils import safe_path, safeguard

from cromlech.browser import IRequest, IResponse
from cromlech.browser import IPublisher, IView, IResponseFactory

from zope.interface import implements
from zope.location import LocationProxy, locate


shortcuts = {
    '@@': dawnlight.VIEW,
    }

base_model_lookup = ModelLookup()
base_view_lookup = ViewLookup()


def safe_unicode(str, enc='utf-8'):
    if isinstance(str, unicode):
        return str
    return unicode(str, enc)


class PublicationError(Exception):
    pass


@crom.implements(IPublisher)
class DawnlightPublisher(object):
    """A publisher using model and view lookup components.
    """

    def __init__(self,
                 model_lookup=base_model_lookup,
                 view_lookup=base_view_lookup):
        self.model_lookup = model_lookup
        self.view_lookup = view_lookup

    def base_path(self, request):
        path = safe_path(request.path)
        script_name = safe_unicode(request.script_name)
        if path.startswith(script_name):
            return path[len(script_name):]
        return path

    @safeguard
    def publish(self, request, root, handle_errors):
        path = self.base_path(request)
        stack = dawnlight.parse_path(path, shortcuts)

        model, crumbs = self.model_lookup(request, root, stack)
        if IResponse.providedBy(model):
            # The found object can be returned safely.
            return model

        if IResponseFactory.providedBy(model):
            return model()

        # The model needs an renderer
        component = self.view_lookup(request, model, crumbs)
        if component is None:
            raise PublicationError('%r can not be rendered.' % model)

        # This renderer needs to be resolved into an IResponse
        factory = IResponseFactory(component)
        return factory()


@crom.adapter
@crom.sources(IRequest, Exception)
@crom.target(IResponseFactory)
def exception_view(request, exception):
    view = IView(exception, request)
    if view is not None:
        # Make sure it's properly located.
        located = LocationProxy(view)
        locate(view, exception, name='exception')
        return IResponseFactory(view)
    return None
