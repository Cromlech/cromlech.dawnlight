# -*- coding: utf-8 -*-

from zope.interface import Interface


class IDawnlightApplication(Interface):
    """Application using the dawnlight publication mechanism.
    """

from dawnlight import ResolveError  # exposing for convenience.
from cromlech.dawnlight.lookup import ModelLookup
from cromlech.dawnlight.lookup import query_http_renderer
from cromlech.dawnlight.lookup import renderer_locator, renderer_protector

from cromlech.dawnlight.publish import DawnlightPublisher
from cromlech.dawnlight.publish import PublicationError, PublicationErrorBubble
from cromlech.dawnlight.consume import AttributeConsumer, ItemConsumer
from cromlech.dawnlight.consume import TraverserConsumer
