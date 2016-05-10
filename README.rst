|travis-badge| |gitter-badge|

.. |travis-badge| image:: https://travis-ci.org/jonashaag/klaus.svg?branch=master
    :target: https://travis-ci.org/jonashaag/klaus

.. |gitter-badge| image:: https://badges.gitter.im/Join%20Chat.svg
   :alt: Join the chat at https://gitter.im/jonashaag/klaus
   :target: https://gitter.im/jonashaag/klaus?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

klaus: a simple, easy-to-set-up Git web viewer that Just Works™.
================================================================

(If it doesn't Just Work for you, please file a bug.)

* Super easy to set up -- no configuration required
* Supports Python 2 and Python 3
* Syntax highlighting
* Git Smart HTTP support
* Code navigation using Exuberant ctags

:Demo: http://klausdemo.lophus.org
:Mailing list: http://groups.google.com/group/klaus-users
:On PyPI: http://pypi.python.org/pypi/klaus/
:Wiki: https://github.com/jonashaag/klaus/wiki
:License: ISC (BSD)


Contributing
------------
Please do it!

I'm equally happy with bug reports/feature ideas and code contributions.
If you have any questions/issues, I'm happy to help!

For starters, `here are a few ideas what to work on. <https://github.com/jonashaag/klaus/issues?q=is%3Aissue+is%3Aopen+label%3A%22C%3A+1%22>`_ :-)


|img1|_ |img2|_ |img3|_

.. |img1| image:: http://i.imgur.com/2XhZIgw.png
.. |img2| image:: http://i.imgur.com/6LjC8Cl.png
.. |img3| image:: http://i.imgur.com/EYJdQwv.png

.. _img1: http://i.imgur.com/MV3uFvw.png
.. _img2: http://i.imgur.com/9HEZ3ro.png
.. _img3: http://i.imgur.com/kx2HaTq.png


Installation
------------
::

   pip install klaus

(Optional dependencies: see `Markup rendering <https://github.com/jonashaag/klaus/wiki/Markup-rendering>`_ in the wiki.)

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

An example WSGI helper script is provided with klaus (see ``klaus/contrib/wsgi.py``),
configuration being read from environment variables. Use it like this (uWSGI example)::

   uwsgi -w klaus.contrib.wsgi \
         --env KLAUS_SITE_NAME="Klaus Demo" \
         --env KLAUS_REPOS="/path/to/repo1 /path/to/repo2 ..." \
         ...

Gunicorn example::

   gunicorn --env KLAUS_SITE_NAME="Klaus Demo" \
            --env KLAUS_REPOS="/path/to/repo1 /path/to/repo2 ..." \
            klaus.contrib.wsgi

See also `deployment section in the wiki <https://github.com/jonashaag/klaus/wiki#deployment>`_.

.. _wsgiref: http://docs.python.org/library/wsgiref.html
