Introduction
============

This package provides a publication mechanism based on `dawnlight`
and the `crom` registry.


Publisher
---------

The Publisher is a component composed of 2 lookups:

  - ModelLookup
  - ViewLookup

The publishing operation is a sequential call of these lookups.


Traversing
----------

Three consumers are defined by default, in order of use:

- traversal on attribute name
- traversal on containement (__getitem__)
- traversal using adaptation for context and request 
  on `cromlech.browser.Itraverser`

You may add your own consumers through the dedicated registry,
`dawnlight_components`.
