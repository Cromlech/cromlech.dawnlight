# -*- coding: utf-8 -*-
"""Tests meant to be discovered by py.test"""

import pytest
import grokcore.component as grok
from grokcore.component.testing import grok_component

from dawnlight import ViewLookup
from dawnlight.interfaces import IConsumer

from cromlech.browser.testing import TestRequest, TestResponse
from cromlech.browser import IRequest, IResponse
from cromlech.browser import IView, IResponseFactory, IRenderable
from cromlech.browser import IPublisher, ITraverser
from cromlech.dawnlight.directives import traversable
from cromlech.dawnlight import (
    ResolveError, IDawnlightApplication, DawnlightPublisher,
    PublicationError, PublicationErrorBubble)

from zope.interface import Interface, implements
from zope.testing.cleanup import cleanUp
from zope.component import (
    queryMultiAdapter, provideAdapter, ComponentLookupError)
from zope.location import LocationProxy


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

    def __init__(self, component):
        self.component = component

    def __call__(self):
        self.component.update()
        body = self.component.render()
        response = TestResponse(body)
        return response
    

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


class Application(object):
    grok.implements(IDawnlightApplication)


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


def test_get_publisher():
    """Publisher is an adapter on IRequest, IDawnlightApplication
    """
    assert queryMultiAdapter(
        (TestRequest(), Application()), IPublisher) is not None


def test_path_parsing():
    root = get_structure()

    req = TestRequest(path=u"/éléonore")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root[u"éléonore"]


def test_attribute_traversing():
    """test that attributes traversing works"""
    root = get_structure()

    req = TestRequest(path="/a")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root.a

    req = TestRequest(path="/_b")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root._b


def test_private_attribute_not_traversing():
    """test that traversing on private attributes does not works"""
    root = get_structure()

    req = TestRequest(path="/c")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(ResolveError):
        publisher.publish(root)

    req = TestRequest(path="/not_existing")
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
    root['a'] = Model()
    req = TestRequest(path="/a")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root.a
    assert publisher.publish(root) != root['a']


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
    """test for raising ResolveError.
    """
    root = get_structure()
    req = TestRequest(path="/b/@@unknown")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(ResolveError):
        publisher.publish(root)


def test_urlencoded_path():
    """test urlencoded path
    """
    root = Container()
    setattr(root, "à", Model())
    root[u"â ñ"] = Model()
    
    req = TestRequest(path="/%C3%A0")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == getattr(root, 'à')

    req = TestRequest(path="/%C3%A2%20%C3%B1")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root[u"â ñ"]


def test_uncomplete_publication():
    """test for raising PublicationError.
    """
    root = get_structure()

    # no more default publisher
    def no_lookup(request, result, crumbs):
        return None

    req = TestRequest(path="/a")
    publisher = DawnlightPublisher(req, Application(), view_lookup=no_lookup)
    with pytest.raises(PublicationError):
        publisher.publish(root)


class AttributeErrorView(RawView):
    
    def __call__(self):
        return u"AttributeError caught on %s" % self.context.__parent__


class InnocentView(RawView):
    
    def __call__(self):
        return "%r is innocent !" % self.context


def test_unproxification():
    """test for unproxified error view publishing.
    """
    root = get_structure()
    
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

    publisher = DawnlightPublisher(
        req, Application(), view_lookup=ViewLookup(lookup=wrap_http_renderer))

    assert publisher.publish(root) == u"AttributeError caught on %s" % root


class NotImplementedView(RawView):
    
    def __call__(self):
        return u"Not implemented: %s" % self.__parent__


class FaultyInit(RawView):
    
    def __init__(self, context, request):
        raise NotImplementedError('init failed')


class FaultyCaller(RawView):
    
    def __call__(self):
        raise NotImplementedError('call failed')


class LookupFailure(RawView):
    
    def __call__(self):
        raise ComponentLookupError('This is bad.')


def test_faulty_resolution():
    root = get_structure()

    # Fail on the renderer init
    provideAdapter(FaultyInit, (IModel, IRequest),
                   IView, name=u'faulty_init')
    
    req = TestRequest(path="/a/faulty_init")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(NotImplementedError) as e:
        publisher.publish(root)
        assert e.value == 'init failed'

    # Fail in the renderer call
    provideAdapter(FaultyCaller, (IModel, IRequest),
                   IView, name=u'faulty_caller')

    req = TestRequest(path="/a/faulty_caller")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(NotImplementedError) as e:
        publisher.publish(root)
        assert e.value == 'call failed'

    # We can render errors
    provideAdapter(
        NotImplementedView, (NotImplementedError, IRequest), IView)

    req = TestRequest(path="/a/faulty_caller")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == u'Not implemented: call failed'

    # Simulation of a component lookup error
    provideAdapter(LookupFailure, (IModel, IRequest),
                   IView, name=u'fail_lookup')

    req = TestRequest(path="/a/fail_lookup")
    publisher = DawnlightPublisher(req, Application())
    with pytest.raises(PublicationErrorBubble) as e:
        publisher.publish(root)

    assert e.value.__class__ == PublicationErrorBubble
    assert e.value.wrapped.__class__ == ComponentLookupError


def test_consumer_returning_view():

    class ViewReturningConsumer(grok.Subscription):
        grok.implements(IConsumer)
        grok.context(Interface)

        def __call__(self, request, obj, stack):
            view = RawView(obj, request)
            return True, view, []

    grok_component('consumer', ViewReturningConsumer)

    root = get_structure()
    req = TestRequest(path="/it_will_return_a_view")
    publisher = DawnlightPublisher(req, Application())
    assert publisher.publish(root) == root

    # The same test fail if we don't use the provided ViewLookup
    publisher = DawnlightPublisher(
        req, Application(), view_lookup=ViewLookup(lookup=wrap_http_renderer))
    with pytest.raises(ResolveError) as e:
        publisher.publish(root) == root
