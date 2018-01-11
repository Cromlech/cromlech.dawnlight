# -*- coding: utf-8 -*-
"""
Some directives related to traversal
"""

from grokker import validator, ArgsDirective


def freeze(component, name, value):
    setattr(component, name, frozenset(value))
    

traversable = ArgsDirective(
    'traversable', 'dawnlight',
    validator=validator.str_validator, set_policy=freeze)
