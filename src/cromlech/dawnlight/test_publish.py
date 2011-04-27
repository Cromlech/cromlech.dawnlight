# -*- coding: utf-8 -*-
"""Tests meant to be discovered by py.test"""

import testing
from cromlech.io.interfaces import IPublisher, IRequest
from cromlech.browser.interfaces import IHTTPRenderer
from zope.interface import Interface
import grokcore.component as grok
from cromlech.io.testing import TestRequest
from cromlech.dawnlight import IDawnlightApplication
from zope.component import queryMultiAdapter, provideAdapter
from cromlech.dawnlight.publish import DawnlightPublisher


def setup_module(module):
    """ grok the publish module
    """
    testing.grok("cromlech.dawnlight.publish")
    provideAdapter(RawView, (Interface, IRequest), IHTTPRenderer, name=u'index')

def teardown_module(module):
    """ undo groking
    """
    testing.cleanUp()

class Application(object):
    grok.implements(IDawnlightApplication)


class Container(dict):
    pass


class Model(object):
    pass


class RawView(object):
    grok.implements(IHTTPRenderer)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def namespace(self):
        pass

    def update(self):
        pass

    def render(self):
        pass

    def __call__(self):
        return self.context



def get_structure():
    """
    initialize a simple structure : a root with a model as attribute "a",
    a model contained as item b
    """
    root = Container()
    setattr(root, "a", Model())
    root["b"] = Model()
    return root

def test_get_publisher():
    assert (queryMultiAdapter((TestRequest(), Application()),
                                         IPublisher) 
            is not None)

def test_attribute_traversing():
    """test that attributes traversing works"""
    root = get_structure()
    req = TestRequest(path="/a")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root.a

