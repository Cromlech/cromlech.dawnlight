# -*- coding: utf-8 -*-

from zope.interface import Interface


class ITracebackAware(Interface):
    """A traceback aware error component.
    """

    def set_exc_info(exc_info):
        """Sets up the exception context using the sys exc_info.
        """
