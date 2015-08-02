Changelog
=========

0.6.0 (TBA)
-----------
* Basic blame view (Martin Zimmermann, Jonas Haag)
* Bug #133: Fix line highlighter (Jonas Haag)

0.5.0 (July 27, 2015)
---------------------
* Experimental support for Python 3. (Jonas Haag)
* #126: Show committer if different from author (Jonas Haag)
* Bug #130: Fix highlighting for "No newline at the end of file" (Jonas Haag)

0.4.10 (June 28, 2015)
----------------------
* Add option to require HTTP authentication for all parts of the Web interface (Jonas Haag)
* Add option to disable authentication entirely for Smart HTTP -- DANGER ZONE! (Jonas Haag)
* Add some unit tests; Travis (Jonas Haag)
* Bugs #116, #124, #128: Fix ``klaus.contrib.wsgi_autoreload`` (William Hughes, Yed Podtrzitko)
* Bug #113: Fix filenames containing whitespace in diffs. (Jonas Haag)
* Bug #115: In diffs, it now says "(new empty file)" rather than "(no changes)" when an empty file has been added. (Jonas Haag)
* Bug #125: Fix tarball download on Python 2.6 (Dana Runge)

0.4.9 (April 13, 2015)
----------------------
* Add option to auto-launch a web-browser on startup (@rjw57)
* Bug #104: "git" executable unnecessarily required to be available (@Mechazawa)

0.4.8 (June 22, 2014)
---------------------
* Fix .tar.gz download if repository contains git submodule. (Jonas Haag)

0.4.7 (June 22, 2014)
---------------------
* #87, #98: Add favicon (@lb1a)
* #35, #95: Add default robots.txt file (@lb1a)
* #93, #94, #101: Add "download as .tar.gz archive" feature. (@Mechazawa, Jonas Haag)
* Bug #90: htdigest file handling broken in contrib.wsgi. (Philip Dexter)
* Bug #99/#53: Misbehaving mimetype recognition (@Mechazawa)

0.4.6 (Mar 5, 2014)
-------------------
* #89: Work around a bug in Dulwich 0.9.5: https://github.com/jelmer/dulwich/issues/144
  (Klaus Alexander Seistrup, Jonas Haag)

0.4.5 (Mar 5, 2014)
-------------------
* Bugfix release for bugfix release 0.4.4. (Daniel Krüger, Jonas Haag)

0.4.4 (Feb 21, 2014)
-------------------
* Fix syntax highlighting in case multiple different file formats share the
  same file extension.  Rely on Pygments to select the best matching lexer for us.
  (Gnewbee, Jonas Haag)

0.4.3 (Feb 20, 2014)
--------------------
* Bug #86: Empty repo name if klaus is fed a ".git" directory.
  Now: name of parent directory, i.e. /foo/bar/.git has the name "bar".
  (David Wahlund)

0.4.2 (Jan 21, 2014)
--------------------
* Bug #83: Wrong version of Dulwich dependency in ``setup.py``

0.4.1 (Jan 17, 2014)
--------------------
* Bug #82: Include ``contrib/*`` in the distribution as ``klaus.contrib.*``.

0.4 (Jan 16, 2014)
------------------
* NOTE TO CONTRIBUTORS -- HISTORY REWRITTEN: See 46bcec1a8e21d510f3af3c9e2d19bc388b20c753
* Moved ``klaus.wsgi`` to ``klaus.contrib.wsgi``
* New autoreloader (see ``klaus/contrib/wsgi_autoreload.py``) WSGI middleware
  that watches a directory for repository additions/deletions
  (i.e., no need to restart klaus anymore).  Also see page in wiki.
  (Jonas Haag)
* Commit view:
   - Wrap long lines (Brendan Molloy)
   - Add change summary and make file diffs toggleable (A. Svensson, Jonas Haag)
   - Speed up page rendering thanks to Javascript optimization (Martin Zimmermann, Jonas Haag)

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
