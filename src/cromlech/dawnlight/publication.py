# -*- coding: utf-8 -*-

import logging
import transaction
import zope.component
import zope.component.interfaces

from cromlech.zope.interfaces import AfterTraverseEvent
from ZODB.POSException import ConflictError
from zope.browser.interfaces import ISystemErrorView
from zope.component import queryMultiAdapter
from zope.event import notify
from zope.interface import implements
from zope.location import LocationProxy
from zope.publisher.defaultview import queryDefaultViewName
from zope.publisher.interfaces import EndRequestEvent, StartRequestEvent
from zope.publisher.interfaces import IExceptionSideEffects, IHeld
from zope.publisher.interfaces import IPublication, IPublishTraverse
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound, Retry
from zope.publisher.publish import mapply
from zope.security.checker import ProxyFactory
from zope.security.proxy import removeSecurityProxy
from zope.traversing.interfaces import BeforeTraverseEvent
from zope.traversing.interfaces import TraversalError
from zope.traversing.namespace import namespaceLookup, nsParse


class Cleanup(object):

    implements(IHeld)

    def __init__(self, f):
        self._f = f

    def release(self):
        self._f()
        self._f = None

    def __del__(self):
        if self._f is not None:
            logging.getLogger('SiteError').error(
                "Cleanup without request close")
            self._f()


class BasePublication(object):
    """Base Zope publication specification."""
    implements(IPublication)

    def __init__(self, root):
        self.root = root

    def proxy(self, ob):
        """Security-proxy an object. Override to change policy.
        """
        return ProxyFactory(ob)

    def beforeTraversal(self, request):
        notify(StartRequestEvent(request))
        transaction.begin()

    def callTraversalHooks(self, request, ob):
        notify(BeforeTraverseEvent(ob, request))

    def afterTraversal(self, request, ob):
        notify(AfterTraverseEvent(ob, request))

    def getApplication(self, request):
        return self.proxy(self.root)

    def traverseName(self, request, ob, name):
        nm = name  # the name to look up the object with

        if name and name[:1] in '@+':
            # Process URI segment parameters.
            ns, nm = nsParse(name)
            if ns:
                try:
                    ob2 = namespaceLookup(ns, nm, ob, request)
                except TraversalError:
                    raise NotFound(ob, name)

                return self.proxy(ob2)

        if nm == '.':
            return ob

        if IPublishTraverse.providedBy(ob):
            ob2 = ob.publishTraverse(request, nm)
        else:
            # self is marker
            adapter = queryMultiAdapter((ob, request), IPublishTraverse,
                                        default=self)
            if adapter is not self:
                ob2 = adapter.publishTraverse(request, nm)
            else:
                raise NotFound(ob, name, request)

        return self.proxy(ob2)

    def callObject(self, request, ob):
        return mapply(ob, request.getPositionalArguments(), request)

    def afterCall(self, request, ob):
        txn = transaction.get()
        if txn.isDoomed():
            txn.abort()
        else:
            txn.commit()

    def endRequest(self, request, ob):
        notify(EndRequestEvent(ob, request))

    def handleException(self, object, request, exc_info, retry_allowed=True):
        # This transaction had an exception that reached the publisher.
        # It must definitely be aborted.
        try:
            transaction.abort()
        except:
            raise

        # Reraise Retry exceptions for the publisher to deal with.
        if retry_allowed and isinstance(exc_info[1], Retry):
            raise

        # Convert ConflictErrors to Retry exceptions.
        if retry_allowed and isinstance(exc_info[1], ConflictError):
            tryToLogWarning(
                'ZopePublication',
                'Competing writes/reads at %s: %s'
                % (request.get('PATH_INFO', '???'),
                   exc_info[1],
                   ),
                )
            raise Retry(exc_info)
        # Are there any reasons why we'd want to let application-level error
        # handling determine whether a retry is allowed or not?
        # Assume not for now.

        response = request.response
        response.reset()
        exception = None
        legacy_exception = not isinstance(exc_info[1], Exception)
        if legacy_exception:
            response.handleException(exc_info)
            if isinstance(exc_info[1], str):
                tryToLogWarning(
                    'Publisher received a legacy string exception: %s.'
                    ' This will be handled by the request.' %
                    exc_info[1])
            else:
                tryToLogWarning(
                    'Publisher received a legacy classic class exception: %s.'
                    ' This will be handled by the request.' %
                    exc_info[1].__class__)
        else:
            # We definitely have an Exception
            # Set the request body, and abort the current transaction.
            self.beginErrorHandlingTransaction(
                request, object, 'application error-handling')
            view = None
            try:
                # We need to get a location, because some template content of
                # the exception view might require one.
                #
                # The object might not have a parent, because it might be a
                # method. If we don't have a `__parent__` attribute but have
                # an im_self or a __self__, use it.
                loc = object
                if not hasattr(object, '__parent__'):
                    loc = removeSecurityProxy(object)
                    # Try to get an object, since we apparently have a method
                    # Note: We are guaranteed that an object has a location,
                    # so just getting the instance the method belongs to is
                    # sufficient.
                    loc = getattr(loc, 'im_self', loc)
                    loc = getattr(loc, '__self__', loc)
                    # Protect the location with a security proxy
                    loc = self.proxy(loc)

                # Give the exception instance its location and look up the
                # view.
                exception = LocationProxy(exc_info[1], loc, '')
                name = queryDefaultViewName(exception, request)
                if name is not None:
                    view = zope.component.queryMultiAdapter(
                        (exception, request), name=name)
            except:
                # Problem getting a view for this exception. Log an error.
                tryToLogException(
                    'Exception while getting view on exception')

            if view is not None:
                try:
                    # We use mapply instead of self.callObject here
                    # because we don't want to pass positional
                    # arguments.  The positional arguments were meant
                    # for the published object, not an exception view.
                    body = mapply(view, (), request)
                    response.setResult(body)
                    transaction.commit()
                    if (ISystemErrorView.providedBy(view)
                        and view.isSystemError()):
                        # Got a system error, want to log the error

                        # Lame hack to get around logging missfeature
                        # that is fixed in Python 2.4
                        try:
                            raise exc_info[0], exc_info[1], exc_info[2]
                        except:
                            logging.getLogger('SiteError').exception(
                                str(request.URL),
                                )

                except:
                    # Problem rendering the view for this exception.
                    # Log an error.
                    tryToLogException(
                        'Exception while rendering view on exception')
                    view = None

            if view is None:
                # Either the view was not found, or view was set to None
                # because the view couldn't be rendered. In either case,
                # we let the request handle it.
                response.handleException(exc_info)
                transaction.abort()

            # See if there's an IExceptionSideEffects adapter for the
            # exception
            try:
                adapter = IExceptionSideEffects(exception, None)
            except:
                tryToLogException(
                    'Exception while getting IExceptionSideEffects adapter')
                adapter = None

            if adapter is not None:
                self.beginErrorHandlingTransaction(
                    request, object, 'application error-handling side-effect')
                try:
                    # Although request is passed in here, it should be
                    # considered read-only.
                    adapter(object, request, exc_info)
                    transaction.commit()
                except:
                    tryToLogException(
                        'Exception while calling'
                        ' IExceptionSideEffects adapter')
                    transaction.abort()

    def beginErrorHandlingTransaction(self, request, ob, note):
        txn = transaction.begin()
        txn.note(note)
        return txn


def tryToLogException(arg1, arg2=None):
    if arg2 is None:
        subsystem = 'SiteError'
        message = arg1
    else:
        subsystem = arg1
        message = arg2
    try:
        logging.getLogger(subsystem).exception(message)
    # Bare except, because we want to swallow any exception raised while
    # logging an exception.
    except:
        pass


def tryToLogWarning(arg1, arg2=None, exc_info=False):
    if arg2 is None:
        subsystem = 'SiteError'
        message = arg1
    else:
        subsystem = arg1
        message = arg2
    try:
        logging.getLogger(subsystem).warn(message, exc_info=exc_info)
    # Bare except, because we want to swallow any exception raised while
    # logging a warning.
    except:
        pass


class Publication(BasePublication):
    """Base for HTTP-based protocol publications"""

    def getDefaultTraversal(self, request, ob):
        if IBrowserPublisher.providedBy(ob):
            return ob.browserDefault(request)
        else:
            adapter = queryMultiAdapter((ob, request), IBrowserPublisher)
            if adapter is not None:
                ob, path = adapter.browserDefault(request)
                ob = self.proxy(ob)
                return ob, path
            else:
                # ob is already proxied
                return ob, None

    def afterCall(self, request, ob):
        super(Publication, self).afterCall(request, ob)
        if request.method == 'HEAD':
            request.response.setResult('')
