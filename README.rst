klaus
=====
*a simple Git web viewer that Just Works™.*  (If it doesn't Just Work for you, please file a bug.)

Demo at http://klausdemo.lophus.org

|img1|_ |img2|_ |img3|_

.. |img1| image:: https://github.com/jonashaag/klaus/raw/master/assets/commit-view.thumb.gif
.. |img2| image:: https://github.com/jonashaag/klaus/raw/master/assets/tree-view.thumb.gif
.. |img3| image:: https://github.com/jonashaag/klaus/raw/master/assets/blob-view.thumb.gif

.. _img1: https://github.com/jonashaag/klaus/raw/master/assets/commit-view.gif
.. _img2: https://github.com/jonashaag/klaus/raw/master/assets/tree-view.gif
.. _img3: https://github.com/jonashaag/klaus/raw/master/assets/blob-view.gif


Requirements
------------
* Python 2.6 (2.5 should work, too)
* Werkzeug_
* Jinja2_
* Pygments_
* dulwich_ (>= 0.7.1)

.. _Werkzeug: http://werkzeug.pocoo.org/
.. _Jinja2: http://jinja.pocoo.org/
.. _Pygments: http://pygments.org/
.. _dulwich: http://www.samba.org/~jelmer/dulwich/


Installation
------------
*The same procedure as every year, James.* ::

   virtualenv your-env
   source your-env/bin/activate

   git clone https://github.com/jonashaag/klaus
   cd klaus
   pip install -r requirements.txt


Usage
-----
Using the ``klaus`` script
..................................

::

   $ klaus --help
   $ klaus -i <host> -p <port> /path/to/repo1 [../path/to/repo2 [...]]

Example::

   $ klaus ../klaus ../bjoern

This will make klaus serve the *klaus* and *bjoern* repos at
``127.0.0.1:8080`` using werkzeug's builtin run_simple server.

.. _wsgiref: http://docs.python.org/library/wsgiref.html
.. _bjoern: https://github.com/jonashaag/bjoern

Using a real server ...................

The ``klaus/__init__.py`` module contains a WSGI ``make_app`` function which
returns the app. The repo list is read from the ``KLAUS_REPOS`` environment
variable (space-separated paths).

UWSGI example::

   uwsgi ... -m klaus --env KLAUS_REPOS="/path/to/repo1 /path/to/repo2 ..." ...
