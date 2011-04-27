# -*- coding: utf-8 -*-
"""Tests meant to be discovered by py.test"""

import testing
from cromlech.io.interfaces import IPublisher, IRequest
from cromlech.browser.interfaces import IHTTPRenderer, ITraverser
from zope.interface import Interface
import grokcore.component as grok
from cromlech.io.testing import TestRequest
from cromlech.dawnlight import IDawnlightApplication
from zope.component import queryMultiAdapter, provideAdapter
from cromlech.dawnlight.publish import DawnlightPublisher
import pytest
import dawnlight


def setup_module(module):
    """ grok the publish module
    """
    testing.grok("cromlech.dawnlight.publish")
    provideAdapter(RawView, (Interface, IRequest),
                   IHTTPRenderer, name=u'index')


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


class SpamTraverser(object):
    """seek for attribute _spam_<name>
    """

    grok.implements(ITraverser)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def traverse(self, ns, name):
        return getattr(self.context, '_spam_%s' % name)


def get_structure():
    """
    initialize a simple structure : a root with a model as attribute "a",
    a model contained as item b
    """
    root = Container()
    setattr(root, "a", Model())
    root["b"] = Model()
    root._spam_foo = Model()
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


def test_item_traversing():
    """test that sub item traversing works"""
    root = get_structure()
    req = TestRequest(path="/b")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root['b']


def test_attribute_masquerade_item():
    """test that attributes takes precedence over sub item"""
    root = get_structure()
    root.b = Model()
    req = TestRequest(path="/b")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) != root['b']


def test_traverser_traversing():
    # register traverser for namespace spam
    provideAdapter(SpamTraverser, (Container, IRequest), ITraverser,
                    name=u'spam')
    root = get_structure()
    req = TestRequest(path="/++spam++foo")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root._spam_foo
    req = TestRequest(path="/++spam++bar")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(AttributeError):
        publisher.publish(root)
