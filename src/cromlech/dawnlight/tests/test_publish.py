# -*- coding: utf-8 -*-
"""Tests meant to be discovered by py.test"""

import pytest
import grokcore.component as grok
from grokcore.component.testing import grok_component

from dawnlight import ViewLookup
from dawnlight.interfaces import IConsumer

from cromlech.browser import IPublisher, ITraverser
from cromlech.browser import IRequest, IResponse
from cromlech.browser import IView, IResponseFactory, IRenderable
from cromlech.browser.testing import TestRequest, TestResponse
from cromlech.dawnlight import DawnlightPublisher
from cromlech.dawnlight import ResolveError, PublicationError
from cromlech.dawnlight import traversable

from zope.interface import Interface, implements
from zope.testing.cleanup import cleanUp
from zope.component import (
    queryMultiAdapter, provideAdapter, ComponentLookupError)
from zope.location import LocationProxy
from zope.interface.verify import verifyObject


class FailingProxy(LocationProxy):

    def __call__(self):
        raise AttributeError

    def __getattr__(self, name):
        if name == 'context':
            raise AttributeError
        return LocationProxy.__getattr__(self, name)

    def __getattribute__(self, name):
        if name == 'context':
            raise AttributeError
        return LocationProxy.__getattribute__(self, name)


class RenderableResponseFactory(object):
    implements(IResponseFactory)

    def __init__(self, component):
        self.component = component

    def __call__(self):
        """DISCLAIMER : this is a test implementation that does NOT fulfill
        the contract of sending back a response. This is ONLY meant for test
        and this is not WANTED in a normal application.
        """
        return self.component.context


class Container(dict):

    traversable('a', '_b', 'à')

    a = None
    _b = None
    c = None


class IModel(Interface):
    pass


class Model(object):
    implements(IModel)


class RawView(object):
    grok.implements(IView, IRenderable)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def update(self):
        pass

    def render(self):
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
    setattr(root, "_b", Model())
    setattr(root, "c", Model())
    root[u"éléonore"] = Model()
    root["b"] = Model()
    root._spam_foo = Model()
    return root


def wrap_http_renderer(request, obj, name=""):
    view = queryMultiAdapter((obj, request), IView, name=name)
    if view is not None:
        view = FailingProxy(view)
    return view


def setup_module(module):
    """Grok the publish module
    """
    grok.testing.grok("cromlech.dawnlight")
    provideAdapter(
        RawView, (IModel, IRequest), IView, name=u'index')
    provideAdapter(
        RenderableResponseFactory, (IRenderable,), IResponseFactory)


def teardown_module(module):
    """Undo groking
    """
    cleanUp()


def test_publisher_basics():
    publisher = DawnlightPublisher()
    assert publisher is not None
    assert verifyObject(IPublisher, publisher)


def test_path_parsing():
    root = get_structure()
    publisher = DawnlightPublisher()

    req = TestRequest(path=u"/éléonore")
    assert publisher.publish(req, root) == root[u"éléonore"]


def test_attribute_traversing():
    """test that attributes traversing works"""
    root = get_structure()
    publisher = DawnlightPublisher()

    req = TestRequest(path="/a")
    assert publisher.publish(req, root) == root.a

    req = TestRequest(path="/_b")
    assert publisher.publish(req, root) == root._b


def test_private_attribute_not_traversing():
    """test that traversing on private attributes does not works"""
    root = get_structure()
    publisher = DawnlightPublisher()

    req = TestRequest(path="/c")
    with pytest.raises(ResolveError):
        publisher.publish(req, root)

    req = TestRequest(path="/not_existing")
    with pytest.raises(ResolveError):
        publisher.publish(req, root)


def test_item_traversing():
    """test that sub item traversing works.
    """
    root = get_structure()
    publisher = DawnlightPublisher()

    req = TestRequest(path="/b")
    assert publisher.publish(req, root) == root['b']


def test_end_with_slash():
    root = get_structure()
    publisher = DawnlightPublisher()

    req = TestRequest(path="/b/")
    assert publisher.publish(req, root) == root['b']

    req = TestRequest(path="/b///")
    assert publisher.publish(req, root) == root['b']


def test_attribute_masquerade_item():
    """test that attributes takes precedence over sub item.
    """
    root = get_structure()
    root['a'] = Model()
    publisher = DawnlightPublisher()
    
    req = TestRequest(path="/a")
    assert publisher.publish(req, root) == root.a
    assert publisher.publish(req, root) != root['a']


def test_traverser_traversing():
    root = get_structure()
    publisher = DawnlightPublisher()

    # register traverser for namespace spam
    provideAdapter(
        SpamTraverser, (Container, IRequest), ITraverser, name=u'spam')

    req = TestRequest(path="/++spam++foo")
    assert publisher.publish(req, root) == root._spam_foo

    req = TestRequest(path="/++spam++bar")
    with pytest.raises(AttributeError):
        publisher.publish(req, root)


def test_script_name():
    """test that request.script_name is taken into account"""
    root = get_structure()
    publisher = DawnlightPublisher()

    req = TestRequest(path="/foo/a", script_name="/foo")
    assert publisher.publish(req, root) == root.a

    req = TestRequest(path="/foo/a", script_name="/bar")
    with pytest.raises(ResolveError):
        publisher.publish(req, root)
                  
    req = TestRequest(path="/a", script_name="/foo")
    assert publisher.publish(req, root) == root.a


def test_no_view():
    """test for raising ResolveError.
    """
    root = get_structure()
    publisher = DawnlightPublisher()

    req = TestRequest(path="/b/@@unknown")
    with pytest.raises(ResolveError):
        publisher.publish(req, root)


def test_urlencoded_path():
    """test urlencoded path
    """
    root = Container()
    setattr(root, "à", Model())
    root[u"â ñ"] = Model()
    publisher = DawnlightPublisher()

    req = TestRequest(path="/%C3%A0")
    assert publisher.publish(req, root) == getattr(root, 'à')

    req = TestRequest(path="/%C3%A2%20%C3%B1")
    assert publisher.publish(req, root) == root[u"â ñ"]


def test_uncomplete_publication():
    """test for raising PublicationError.
    """
    # no more default publisher
    def no_lookup(request, result, crumbs):
        return None

    root = get_structure()
    publisher = DawnlightPublisher(view_lookup=no_lookup)

    req = TestRequest(path="/a")
    with pytest.raises(PublicationError):
        publisher.publish(req, root)


class AttributeErrorView(RawView):
    implements(IResponseFactory)

    def __call__(self):
        return u"AttributeError on %s" % self.context.__parent__.__class__


class InnocentView(RawView):
    implements(IResponseFactory)

    def __call__(self):
        return "%r is innocent !" % self.context


def test_unproxification():
    """test for unproxified error view publishing.
    """
    root = get_structure()
    publisher = DawnlightPublisher(
        view_lookup=ViewLookup(lookup=wrap_http_renderer))

    provideAdapter(
        AttributeErrorView, (AttributeError, IRequest), IView)

    provideAdapter(
        InnocentView, (IModel, IRequest), IView, name="innocent")

    req = TestRequest(path="/a/@@innocent")
    proxified = wrap_http_renderer(req, root.a, "innocent")

    with pytest.raises(AttributeError):
        proxified.context

    with pytest.raises(AttributeError):
        proxified()

    assert publisher.publish(req, root) == (
        u"AttributeError on <class 'cromlech.dawnlight.tests."
        u"test_publish.Container'>")


class NotImplementedView(RawView):
    implements(IResponseFactory)

    def __call__(self):
        return u"Not implemented: %s" % self.__parent__


class FaultyInit(RawView):
    implements(IResponseFactory)

    def __init__(self, context, request):
        raise NotImplementedError('init failed')


class FaultyCaller(RawView):
    implements(IResponseFactory)
    
    def __call__(self):
        raise NotImplementedError('call failed')


class LookupFailure(RawView):
    implements(IResponseFactory)

    def __call__(self):
        raise ComponentLookupError('This is bad.')


def test_faulty_resolution():
    root = get_structure()
    publisher = DawnlightPublisher()

    # Fail on the renderer init
    provideAdapter(FaultyInit, (IModel, IRequest),
                   IView, name=u'faulty_init')
    
    req = TestRequest(path="/a/faulty_init")
    with pytest.raises(NotImplementedError) as e:
        publisher.publish(req, root)
        assert e.value == 'init failed'

    # Fail in the renderer call
    provideAdapter(FaultyCaller, (IModel, IRequest),
                   IView, name=u'faulty_caller')

    req = TestRequest(path="/a/faulty_caller")
    with pytest.raises(NotImplementedError) as e:
        publisher.publish(req, root)

    # We can render errors
    provideAdapter(
        NotImplementedView, (NotImplementedError, IRequest), IView)

    req = TestRequest(path="/a/faulty_caller")
    assert publisher.publish(req, root) == u'Not implemented: call failed'

    # Simulation of a component lookup error
    provideAdapter(LookupFailure, (IModel, IRequest),
                   IView, name=u'fail_lookup')

    req = TestRequest(path="/a/fail_lookup")
    with pytest.raises(ComponentLookupError) as e:
        publisher.publish(req, root)


def test_consumer_returning_view():

    class ViewReturningConsumer(grok.Subscription):
        grok.implements(IConsumer)
        grok.context(Interface)

        def __call__(self, request, obj, stack):
            view = RawView(obj, request)
            return True, view, []

    grok_component('consumer', ViewReturningConsumer)

    root = get_structure()
    publisher = DawnlightPublisher()

    req = TestRequest(path="/it_will_return_a_view")
    assert publisher.publish(req, root) == root

    # The same test fail if we don't use the provided ViewLookup
    publisher = DawnlightPublisher(
        view_lookup=ViewLookup(lookup=wrap_http_renderer))
    with pytest.raises(ResolveError) as e:
        publisher.publish(req, root) == root
