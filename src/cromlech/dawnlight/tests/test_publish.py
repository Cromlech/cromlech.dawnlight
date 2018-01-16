# -*- coding: utf-8 -*-

import crom
import pytest

from collections import deque
from crom import testing
from crom.implicit import implicit
from dawnlight import ViewLookup
from dawnlight.interfaces import IConsumer

from cromlech.dawnlight.registry import dawnlight_components
from cromlech.browser import IPublisher, ITraverser
from cromlech.browser import IRequest, IResponse
from cromlech.browser import IView, IResponseFactory, IRenderable
from cromlech.browser.testing import TestRequest as Request
from cromlech.dawnlight import DawnlightPublisher
from cromlech.dawnlight import ResolveError, PublicationError
from cromlech.dawnlight import traversable, safeguard
from cromlech.dawnlight.utils import query_view

from zope.interface import Interface, implementer
from crom import ComponentLookupError
from zope.location import LocationProxy, ILocation
from zope.interface.verify import verifyObject


@traversable('a', '_b', 'à')
class Container(dict):

    a = None
    _b = None
    c = None


class IModel(Interface):
    pass


@implementer(IModel)
class Model(object):
    pass


@implementer(ILocation, IView, IRenderable)
class RawView(object):

    __parent__ = None
    __name__ = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def update(self):
        pass

    def render(self):
        return self.context


@implementer(ITraverser)
class SpamTraverser(object):
    """a traverser that seeks for attribute _spam_<name>
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def traverse(self, ns, name):
        return getattr(self.context, '_spam_%s' % name)


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


@implementer(IResponseFactory)
class RenderableResponseFactory(object):

    def __init__(self, component):
        self.component = component

    def __call__(self):
        """DISCLAIMER : this is a test implementation that does NOT fulfill
        the contract of sending back a response. This is ONLY meant for test
        and this is not WANTED in a normal application.
        """
        return self.component.context


def setup_module(module):
    import cromlech.dawnlight

    testing.setup()
    crom.configure(cromlech.dawnlight)
    crom.implicit.registry.register(
        (Interface, IRequest), IView, 'index', RawView)
    crom.implicit.registry.register(
        (IRenderable,), IResponseFactory, '', RenderableResponseFactory)


def teardown_module(module):
    testing.teardown()


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
    root["éléonore"] = Model()
    root["b"] = Model()
    root._spam_foo = Model()
    return root


def wrap_http_renderer(request, obj, name=""):
    view = query_view(request, obj, name)
    if view is not None:
        view = FailingProxy(view)
    return view


def test_publisher_basics():
    publisher = DawnlightPublisher()
    assert publisher is not None
    assert verifyObject(IPublisher, publisher)


def test_unicode_script_name():
    root = get_structure()
    publisher = DawnlightPublisher()

    req = Request(path="/éléonore", script_name='/')
    assert publisher.publish(req, root) == root["éléonore"]
    

def test_path_parsing():
    root = get_structure()
    publisher = DawnlightPublisher()

    req = Request(path="/éléonore")
    assert publisher.publish(req, root) == root["éléonore"]


def test_attribute_traversing():
    """test that attributes traversing works"""
    root = get_structure()
    publisher = DawnlightPublisher()

    req = Request(path="/a")
    assert publisher.publish(req, root) == root.a

    req = Request(path="/_b")
    assert publisher.publish(req, root) == root._b


def test_private_attribute_not_traversing():
    """test that traversing on private attributes does not works"""
    root = get_structure()
    publisher = DawnlightPublisher()

    req = Request(path="/c")
    with pytest.raises(ResolveError):
        publisher.publish(req, root)

    req = Request(path="/not_existing")
    with pytest.raises(ResolveError):
        publisher.publish(req, root)


def test_item_traversing():
    """test that sub item traversing works.
    """
    root = get_structure()
    publisher = DawnlightPublisher()

    req = Request(path="/b")
    assert publisher.publish(req, root) == root['b']


def test_end_with_slash():
    root = get_structure()
    publisher = DawnlightPublisher()

    req = Request(path="/b/")
    assert publisher.publish(req, root) == root['b']

    req = Request(path="/b///")
    assert publisher.publish(req, root) == root['b']


def test_attribute_masquerade_item():
    """test that attributes takes precedence over sub item.
    """
    root = get_structure()
    root['a'] = Model()
    publisher = DawnlightPublisher()
    
    req = Request(path="/a")
    assert publisher.publish(req, root) == root.a
    assert publisher.publish(req, root) != root['a']


def test_traverser_traversing():
    root = get_structure()
    publisher = DawnlightPublisher()

    # register traverser for namespace spam
    crom.implicit.registry.register(
        (Container, IRequest), ITraverser, 'spam', SpamTraverser)

    req = Request(path="/++spam++foo")
    assert publisher.publish(req, root) == root._spam_foo

    req = Request(path="/++spam++bar")
    with pytest.raises(AttributeError):
        publisher.publish(req, root)


def test_script_name():
    """test that request.script_name is taken into account"""
    root = get_structure()
    publisher = DawnlightPublisher()

    req = Request(path="/foo/a", script_name="/foo")
    assert publisher.publish(req, root) == root.a

    req = Request(path="/foo/a", script_name="/bar")
    with pytest.raises(ResolveError):
        publisher.publish(req, root)
                  
    req = Request(path="/a", script_name="/foo")
    assert publisher.publish(req, root) == root.a


def test_no_view():
    """test for raising ResolveError.
    """
    root = get_structure()
    publisher = DawnlightPublisher()

    req = Request(path="/b/@@unknown")
    with pytest.raises(ResolveError):
        publisher.publish(req, root)


def test_urlencoded_path():
    """test urlencoded path
    """
    root = Container()
    setattr(root, "à", Model())
    root["â ñ"] = Model()
    publisher = DawnlightPublisher()

    req = Request(path="/%C3%A0")
    assert publisher.publish(req, root) == getattr(root, 'à')

    req = Request(path="/%C3%A2%20%C3%B1")
    assert publisher.publish(req, root) == root["â ñ"]


def test_uncomplete_publication():
    """test for raising PublicationError.
    """
    # no more default publisher
    def no_lookup(request, result, crumbs):
        return None

    root = get_structure()
    publisher = DawnlightPublisher(view_lookup=no_lookup)

    req = Request(path="/a")
    with pytest.raises(PublicationError):
        publisher.publish(req, root)


@implementer(IResponseFactory)
class AttributeErrorView(RawView):

    def __call__(self):
        return "AttributeError on %s" % self.context.__parent__.__class__


@implementer(IResponseFactory)
class InnocentView(RawView):

    def __call__(self):
        return "%r is innocent !" % self.context


def test_unproxification():
    """test for unproxified error view publishing.
    """
    root = get_structure()
    publisher = DawnlightPublisher(
        view_lookup=ViewLookup(lookup=wrap_http_renderer))

    implicit.registry.register(
        (AttributeError, IRequest), IView, '', AttributeErrorView)

    implicit.registry.register(
        (IModel, IRequest), IView, 'innocent', InnocentView)

    req = Request(path="/a/@@innocent")
    proxified = wrap_http_renderer(req, root.a, "innocent")

    with pytest.raises(AttributeError):
        proxified.context

    with pytest.raises(AttributeError):
        proxified()

    assert publisher.publish(req, root) == (
        "AttributeError on <class 'cromlech.dawnlight.tests."
        "test_publish.Container'>")

    # we test the error handling deactivation
    with pytest.raises(AttributeError):
        assert publisher.publish(req, root, handle_errors=False)


@implementer(IResponseFactory)
class NotImplementedView(RawView):

    def __call__(self):
        return "Not implemented: %s" % self.__parent__


@implementer(IResponseFactory)
class FaultyInit(RawView):

    def __init__(self, context, request):
        raise NotImplementedError('init failed')


@implementer(IResponseFactory)
class FaultyCaller(RawView):

    def __call__(self):
        raise NotImplementedError('call failed')


@implementer(IResponseFactory)
class LookupFailure(RawView):

    def __call__(self):
        raise ComponentLookupError('This is bad.')


def test_faulty_resolution():
    root = get_structure()
    publisher = DawnlightPublisher()

    # Fail on the renderer init
    crom.implicit.registry.register(
        (IModel, IRequest), IView, 'faulty_init', FaultyInit)
    
    req = Request(path="/a/faulty_init")
    with pytest.raises(NotImplementedError) as e:
        publisher.publish(req, root)
        assert e.value == 'init failed'

    # Fail in the renderer call
    crom.implicit.registry.register(
        (IModel, IRequest), IView, 'faulty_caller', FaultyCaller)

    req = Request(path="/a/faulty_caller")
    with pytest.raises(NotImplementedError) as e:
        publisher.publish(req, root)

    # We can render errors
    crom.implicit.registry.register(
        (NotImplementedError, IRequest), IView, '', NotImplementedView)

    req = Request(path="/a/faulty_caller")
    assert publisher.publish(req, root) == 'Not implemented: call failed'

    # Simulation of a component lookup error
    crom.implicit.registry.register(
        (IModel, IRequest), IView, 'fail_lookup', LookupFailure)

    req = Request(path="/a/fail_lookup")
    with pytest.raises(ComponentLookupError) as e:
        publisher.publish(req, root)


def test_consumer_returning_view():

    class ViewReturningConsumer:

        def __init__(self, context):
            self.context = context
        
        def __call__(self, request, obj, stack):
            view = RawView(obj, request)
            return True, view, deque()

    dawnlight_components.subscribe(
        (Interface,), IConsumer, ViewReturningConsumer)

    root = get_structure()
    publisher = DawnlightPublisher()

    req = Request(path="/it_will_return_a_view")
    assert publisher.publish(req, root) == root
