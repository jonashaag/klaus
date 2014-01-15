Changelog
=========

0.4 (Jan 16, 2014)
------------------
* NOTE TO CONTRIBUTORS -- HISTORY REWRITTEN: See 46bcec1a8e21d510f3af3c9e2d19bc388b20c753
* New autoreloader (see ``contrib/wsgi_autoreload.py``) WSGI middleware that
  watches a directory for repository additions/deletions
  (i.e., no need to restart klaus anymore).  Also see page in wiki.
  (Jonas Haag)
* Commit view:
   - Wrap long lines (Brendan Molloy)
   - Add change summary and make file diffs toggleable (A. Svensson, Jonas Haag)
   - Speed up page rendering thanks to Javascript optimization (Jonas Haag)

0.3 (Jun 10, 2013)
------------------
* #57: Better "N minutes/hours/weeks ago" strings (Jonas Haag)
* #59: Show download link for binary files / large files
* #56: Markdown renderer: enable "TOC" and "extra" extensions (@ar4s, Jonas Haag)
* Bug #61: Don't crash on repos without "master" branch (Jonas Haag)
* Bug #60: Don't crash if "/blob/" URL is requested with non-file argument
* Don't crash on completely empty repos (Jonas Haag)

0.2.3 (May 08, 2013)
--------------------
* Fix an issue with the version/revision indicator bottom-right of the page (Jonas Haag)

0.2.2 (Apr 5, 2013)
-------------------
* #49: Support for short descriptions using `.git/description` file (Ernest W. Durbin III)
* Bug #53: Misbehaving mimetype recognition (Jonas Haag)

0.2.1 (Jan 29, 2013)
--------------------
* Tags work again (Jonas Haag)
* Apache/mod_wsgi deployment docs (Alex Marandon)
* Bug #43: ``bin/klaus``: ``--site-name`` did only accept ASCII strings
  (Alex Marandon, Martin Zimmermann, Jonas Haag)
* More robust routing (Jonas Haag)

0.2 (Dec 3, 2012)
-----------------
* Rewrite/port to Flask/Werkzeug (Martin Zimmermann, Jonas Haag).
* Git Smart HTTP support with HTTP authentication (Martin Zimmermann, Jonas Haag)
* Tag selector (Jonas Haag)
* Switch to ISC license

0.1 (unreleased)
----------------
BSD-licensed initial version, based on Nano "web framework" (Jonas Haag)
