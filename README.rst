klaus
=====
*a simple Git web viewer that Just Works™.*

Requirements
------------
* Python 2.7
* Jinja2_ (``pip install jinja2``)
* Pygments_ (``pip install pygments``)
* dulwich_ (``pip install dulwich``)
* Nano_ (``git submodule update --init``)

.. _Jinja2: http://jinja.pocoo.org/
.. _Pygments: http://pygments.org/
.. _dulwich: http://www.samba.org/~jelmer/dulwich/
.. _Nano: https://github.com/jonashaag/nano

Usage
-----
Using the ``quickstart.py`` script
..................................
::

   ./quickstart --help
   ./quickstart.py <host> <port> /path/to/repo1 [../path/to/repo2 [...]]

Example::

   ./quickstart.py 127.0.0.1 8080 ../klaus ../nano ../bjoern

This will make klaus serve the `klaus`, `nano` and `bjoern` repos at
``127.0.0.1:8080`` using Python's built-in wsgiref_ server (or, if installed,
the bjoern_ server).

.. _wsgiref: http://docs.python.org/library/wsgiref.html
.. _bjoern: https://github.com/jonashaag/bjoern

Using a real server
...................
The ``klaus.py`` module contains an ``app`` object that is a WSGI application.
