# -*- coding: utf-8 -*-

from zope.interface import Interface


class IDawnlightApplication(Interface):
    """Application using the dawnlight publication mechanism"""


from cromlech.dawnlight.publish import ModelLookup, ViewLookup
from cromlech.dawnlight.publish import DawnlightPublisher
from cromlech.dawnlight.publish import (
    AttributeConsumer, ItemConsumer, TraverserConsumer)
