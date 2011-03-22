# -*- coding: utf-8 -*-

import sys
from cromlech.io.interfaces import IPublisher
from cromlech.zope.publication import Publication
from grokcore.component import adapts, MultiAdapter
from zope.component import queryAdapter
from zope.interface import implements, Interface
from zope.publisher.browser import IBrowserRequest
from zope.publisher.interfaces import Retry, IReRaiseException


class ZopePublisher(MultiAdapter):
    implements(IPublisher)
    adapts(IBrowserRequest, Interface)

    def __init__(self, request, app):
        self.app = app
        self.request = request

    def publish(self, root, handle_errors=True):
        to_raise = None
        request = self.request
        request.setPublication(Publication(root))

        while True:
            publication = request.publication
            try:
                try:
                    obj = None
                    try:
                        try:
                            request.processInputs()
                            publication.beforeTraversal(request)

                            obj = publication.getApplication(request)
                            obj = request.traverse(obj)
                            publication.afterTraversal(request, obj)

                            result = publication.callObject(request, obj)
                            response = request.response
                            if result is not response:
                                response.setResult(result)

                            publication.afterCall(request, obj)

                        except:
                            exc_info = sys.exc_info()
                            publication.handleException(
                                obj, request, exc_info, True)

                            if not handle_errors:
                                # Reraise only if there is no adapter
                                # indicating that we shouldn't
                                reraise = queryAdapter(
                                    exc_info[1], IReRaiseException,
                                    default=None)
                                if reraise is None or reraise():
                                    raise
                    finally:
                        publication.endRequest(request, obj)

                    break  # Successful.

                except Retry, retryException:
                    if request.supportsRetry():
                        # Create a copy of the request and use it.
                        newrequest = request.retry()
                        request.close()
                        request = newrequest
                    elif handle_errors:
                        # Output the original exception.
                        publication = request.publication
                        publication.handleException(
                            obj, request,
                            retryException.getOriginalException(), False)
                        break
                    else:
                        to_raise = retryException.getOriginalException()
                        if to_raise is None:
                            # There is no original exception inside
                            # the Retry, so just reraise it.
                            raise
                        break

            except:
                # Bad exception handler or retry method.
                # Re-raise after outputting the response.
                if handle_errors:
                    request.response.internalError()
                    to_raise = sys.exc_info()
                    break
                else:
                    raise

        response = request.response
        if to_raise is not None:
            raise to_raise[0], to_raise[1], to_raise[2]

        # Return the request, since it might be a different object than the one
        # that was passed in.
        return request
