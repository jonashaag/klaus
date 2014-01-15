A simple Git web viewer that Just Works™.
-----------------------------------------

(If it doesn't Just Work for you, please file a bug.)

:Demo: http://klausdemo.lophus.org
:Mailing list: http://groups.google.com/group/klaus-users
:On PyPI: http://pypi.python.org/pypi/klaus/
:License: ISC (BSD)

Contributing
------------
Please do it!

I'm equally happy with bug reports/feature ideas and code contributions.
If you have any questions/issues, I'm happy to help!

For starters, `here are a few ideas what to work on. <https://github.com/jonashaag/klaus/issues>`_ :-)

Features
--------
* Super easy to set up -- no configuration required
* Syntax highlighting
* Git Smart HTTP support


|img1|_ |img2|_ |img3|_

.. |img1| image:: https://github.com/jonashaag/klaus/raw/master/assets/commit-view.thumb.gif
.. |img2| image:: https://github.com/jonashaag/klaus/raw/master/assets/tree-view.thumb.gif
.. |img3| image:: https://github.com/jonashaag/klaus/raw/master/assets/blob-view.thumb.gif

.. _img1: https://github.com/jonashaag/klaus/raw/master/assets/commit-view.gif
.. _img2: https://github.com/jonashaag/klaus/raw/master/assets/tree-view.gif
.. _img3: https://github.com/jonashaag/klaus/raw/master/assets/blob-view.gif


Installation
------------
::

   pip install klaus


Usage
-----

See also: `Klaus wiki <https://github.com/jonashaag/klaus/wiki>`_

Using the ``klaus`` script
^^^^^^^^^^^^^^^^^^^^^^^^^^
**NOTE:** This is intended for testing/low-traffic local installations *only*!
The `klaus` script uses wsgiref_ internally which doesn't scale *at all*
(in fact it's single-threaded and non-asynchronous).

To run klaus using the default options::

   klaus [repo1 [repo2 ...]]

For more options, see::

   klaus --help


Using a real server
^^^^^^^^^^^^^^^^^^^
The ``klaus`` module contains a ``make_app`` function which returns a WSGI app.

An example WSGI helper script is provided with klaus (see ``klaus/wsgi.py``),
configuration being read from environment variables. Use it like this (uWSGI example)::

   uwsgi -w klaus.wsgi \
         --env KLAUS_SITE_TITLE="Klaus Demo" \
         --env KLAUS_REPOS="/path/to/repo1 /path/to/repo2 ..." \
         ...


.. _wsgiref: http://docs.python.org/library/wsgiref.html
