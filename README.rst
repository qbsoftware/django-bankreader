django-bankreader
=================

Pluggable django application for reading and processing various formats of bank account statements.

Installation
------------

* install ``django-bankreader`` either from source or using pip
* add `bankreader` to ``settings.INSTALLED_APPS``
* use ``post_save`` signal to process newly created ``Transaction`` objects
* see the ``demoapp`` application in ``bankreader_demo`` project for more details
