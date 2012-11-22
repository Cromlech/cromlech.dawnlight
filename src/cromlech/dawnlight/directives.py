# -*- coding: utf-8 -*-
"""
Some directives related to traversal
"""

from grokker import validator, ArgsDirective


def freeze(component, name, value):
    frozen = frozenset(value)
    setattr(component, name, value)
    

traversable = ArgsDirective(
    'traversable', 'dawnlight',
    validator=validator.str_validator, set_policy=freeze)
