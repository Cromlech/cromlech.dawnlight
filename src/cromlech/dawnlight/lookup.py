# -*- coding: utf-8 -*-

import dawnlight
import grokcore.component as grok
from cromlech.browser.interfaces import IHTTPRenderer
from dawnlight.interfaces import IConsumer
from zope.component import queryMultiAdapter


def query_http_renderer(request, obj, name=""):
    return queryMultiAdapter((obj, request), IHTTPRenderer, name=name)


class ModelLookup(dawnlight.ModelLookup):

    def __init__(self):
        pass

    def register(self, class_or_interface, consumer):
        """Consumers are intended to be subscription adapters.
        """
        raise NotImplementedError(u"Use the global registry.")

    def lookup(self, obj):
        """We use IConsumer registered in the global registry as
        subscription adapters.
        """
        return grok.querySubscriptions(obj, IConsumer)


class ViewLookup(dawnlight.ViewLookup):

    def __init__(self, lookup=query_http_renderer):
        dawnlight.ViewLookup.__init__(self, lookup)
