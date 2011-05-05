Introduction
============

This package provides a publication mechanism based on dawnlight
for cromlech stack.


Publisher
-------------

The Publisher is a component adapting a IDawnlightApplication and a request.

Getting the publisher as an adapters permits to use different publisher
depending on the application.


Traversing
-------------

Three consumers are defined by default, in order of use :

- traversal on attribute name
- traversal on containement (__getitem__)
- traversal using adaptation for context and request 
  on cromlech.browser.Itraverser

You may add your own consumers through global registry.


Views
---------

View use adapters for object, request on cromlech.browser.IHttpRenderer

Note that this is compatible dolmen.view 
