# -*- coding: utf-8 -*-
"""Tests meant to be discovered by py.test"""

import pytest
import grokcore.component as grok

from cromlech.browser.interfaces import IHTTPRenderer, ITraverser
from cromlech.dawnlight import IDawnlightApplication
from cromlech.dawnlight.publish import (DawnlightPublisher,
                                       PublicationUncomplete)
from cromlech.io.interfaces import IPublisher, IRequest, IResponse
from cromlech.io.testing import TestRequest
from dawnlight import ResolveError
from zope.component import (queryMultiAdapter, provideAdapter,
                            ComponentLookupError)
from zope.interface import Interface, implements
from zope.testing.cleanup import cleanUp


def setup_module(module):
    """Grok the publish module
    """
    grok.testing.grok("cromlech.dawnlight")
    provideAdapter(RawView, (IModel, IRequest),
                   IHTTPRenderer, name=u'index')


def teardown_module(module):
    """Undo groking
    """
    cleanUp()


class Application(object):
    grok.implements(IDawnlightApplication)


class Container(dict):

    _protected_attr = ''
    __special_attr__ = ''
    __private_attr = ''


class IModel(Interface):
    pass


class Model(object):
    implements(IModel)


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
    """a traverser that seeks for attribute _spam_<name>
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
    root as an attribute _spam_foo to test SpamTraverser
    """
    root = Container()
    setattr(root, "a", Model())
    root["b"] = Model()
    root._spam_foo = Model()
    return root


def test_get_publisher():
    """Publisher is an adapter on IRequest, IDawnlightApplication
    """
    assert (queryMultiAdapter((TestRequest(), Application()),
                                IPublisher)
            is not None)


def test_attribute_traversing():
    """test that attributes traversing works"""
    root = get_structure()
    req = TestRequest(path="/a")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root.a


def test_private_attribute_not_traversing():
    """test that traversing on private attributes does not works"""
    root = get_structure()

    req = TestRequest(path="/_protected_attr")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(ResolveError):
        publisher.publish(root)

    req = TestRequest(path="/__private_attr")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(ResolveError):
        publisher.publish(root)

    req = TestRequest(path="/__special_attr__")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(ResolveError):
        publisher.publish(root)


def test_item_traversing():
    """test that sub item traversing works"""
    root = get_structure()

    req = TestRequest(path="/b")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root['b']


def test_end_with_slash():
    root = get_structure()

    req = TestRequest(path="/b/")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root['b']

    req = TestRequest(path="/b///")
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
    root = get_structure()

    # register traverser for namespace spam
    provideAdapter(
        SpamTraverser, (Container, IRequest), ITraverser, name=u'spam')

    req = TestRequest(path="/++spam++foo")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root._spam_foo

    req = TestRequest(path="/++spam++bar")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(AttributeError):
        publisher.publish(root)


def test_script_name():
    """test that request.script_name is taken into account"""
    root = get_structure()
    req = TestRequest(path="/foo/a", script_name="/foo")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root.a

    req = TestRequest(path="/foo/a", script_name="/bar")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(ResolveError):
        publisher.publish(root)
    req = TestRequest(path="/a", script_name="/foo")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root.a


def test_no_view():
    """test for raising PublicationUncomplete"""
    root = get_structure()
    req = TestRequest(path="/b/@@unknown")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(ResolveError):
        publisher.publish(root)


def test_uncomplete_publication():
    """test for raising PublicationUncomplete"""
    root = get_structure()

    # no more default publisher
    def no_lookup(request, result, crumbs):
        return None

    req = TestRequest(path="/a")
    publisher = DawnlightPublisher(req, Application(), view_lookup=no_lookup)
    with pytest.raises(PublicationUncomplete):
        publisher.publish(root)


class FaultyInit(RawView):
    
    def __init__(self, context, request):
        raise NotImplementedError('init failed')


class FaultyCaller(RawView):
    
    def __call__(self):
        raise NotImplementedError('call failed')


@grok.adapter(RawView)
@grok.implementer(IResponse)
def faulty_renderer_adapter(renderer):
    raise ComponentLookupError('failed on purpose')


def test_faulty_resolution():
    root = get_structure()

    # Fail on the renderer init
    provideAdapter(FaultyInit, (IModel, IRequest),
                   IHTTPRenderer, name=u'faulty_init')
    
    req = TestRequest(path="/a/faulty_init")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(NotImplementedError) as e:
        publisher.publish(root)
        assert e.value == 'init failed'

    # Fail in the renderer call
    provideAdapter(FaultyCaller, (IModel, IRequest),
                   IHTTPRenderer, name=u'faulty_caller')

    req = TestRequest(path="/a/faulty_caller")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(NotImplementedError) as e:
        publisher.publish(root)
        assert e.value == 'call failed'

    # Fail in the IResponse adapter
    provideAdapter(faulty_renderer_adapter)

    req = TestRequest(path="/a")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(ComponentLookupError) as e:
        publisher.publish(root)
        assert e.value == 'failed on purpose'
