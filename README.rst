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
* Python 2.7
* Jinja2_
* Pygments_
* dulwich_ (>= 0.7.1)
* argparse (only for Python 2.6)
* Nano_ (shipped as submodule, do a ``git submodule update --init`` to fetch)

.. _Jinja2: http://jinja.pocoo.org/
.. _Pygments: http://pygments.org/
.. _dulwich: http://www.samba.org/~jelmer/dulwich/
.. _Nano: https://github.com/jonashaag/nano


Installation
------------
*The same procedure as every year, James.* ::

   mkdir klaus-site/
   cd klaus-site

   git clone https://github.com/jonashaag/klaus
   cd klaus
   git submodule update --init

   cd ..

   virtualenv your-env
   source your-env/bin/activate

   pip install -r klaus/requirements.txt


Usage
-----
Using the ``quickstart.py`` script
..................................
::

   tools/quickstart --help
   tools/quickstart.py <host> <port> /path/to/repo1 [../path/to/repo2 [...]]

Example::

   tools/quickstart.py 127.0.0.1 8080 ../klaus ../nano ../bjoern

This will make klaus serve the *klaus*, *nano* and *bjoern* repos at
``127.0.0.1:8080`` using Python's built-in wsgiref_ server (or, if installed,
the bjoern_ server).

.. _wsgiref: http://docs.python.org/library/wsgiref.html
.. _bjoern: https://github.com/jonashaag/bjoern

Using a real server
...................
The ``klaus.py`` module contains a WSGI ``application`` object. The repo list
is read from the ``KLAUS_REPOS`` environment variable (space-separated paths).

UWSGI example::

   uwsgi ... -m klaus --env KLAUS_REPOS="/path/to/repo1 /path/to/repo2 ..." ...
