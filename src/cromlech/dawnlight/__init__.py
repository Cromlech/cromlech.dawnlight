# -*- coding: utf-8 -*-

from zope.interface import Interface


class IDawnlightApplication(Interface):
    """Application using the dawnlight publication mechanism.
    """

from dawnlight import ResolveError  # exposing for convenience.
from cromlech.dawnlight.lookup import ModelLookup, ViewLookup
from cromlech.dawnlight.publish import (
    DawnlightPublisher, PublicationError, PublicationErrorBubble)
from cromlech.dawnlight.consume import (
    AttributeConsumer, ItemConsumer, TraverserConsumer)
