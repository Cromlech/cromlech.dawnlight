# -*- coding: utf-8 -*-

from zope.interface import Interface


class IDawnlightApplication(Interface):
    """Application using the dawnlight publication mechanism.
    """


from cromlech.dawnlight.lookup import ModelLookup, ViewLookup
from cromlech.dawnlight.publish import DawnlightPublisher
from cromlech.dawnlight.consume import (
    AttributeConsumer, ItemConsumer, TraverserConsumer)
