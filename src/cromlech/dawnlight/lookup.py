# -*- coding: utf-8 -*-

from dawnlight import ViewLookup, ModelLookup as BaseModelLookup
from dawnlight.interfaces import IConsumer
from grokcore.component import querySubscriptions


class ModelLookup(BaseModelLookup):

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
        return querySubscriptions(obj, IConsumer)
