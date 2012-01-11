# -*- coding: utf-8 -*-
"""
Some directives related to traversal
"""

import martian


class traversable(martian.Directive):
    """specify wich attributes are traversable
    """
    scope = martian.CLASS_OR_MODULE
    store = martian.ONCE
    default = []

    def factory(self, *attrs):
        return frozenset(attrs)
