Changelog
=========

1.5.0 (Nov 3, 2019)
-------------------
- #239: More robust "last updated at" determination (Jelmer Vernooĳ)
- #238: Cache index view (Jonas Haag)
- #240: Handle non-Git folders nicely with autoreloader (Guillaume Hétier)

1.4.0 (May 7, 2019)
-------------------
- #217: Add man page (Jelmer Vernooĳ)
- #229: Better download tarball names (Jelmer Vernooĳ)
- #219: More markdown file extensions (Chris Pressey)
- #237: Default to ordering repositories by last update (Jonas Haag)
- Bug fixes #221, #224, #226, #225, #227, #234, #233 (Christian Ulrich, Jelmer Vernooĳ, Jonas Haag)

1.3.0 (June 19, 2018)
--------------------
- Split `klaus.contrib.autoreload` into main and entrypoint logic so it's
  easier to customise it to your needs. (Jakob Hirsch)
- #212, #213: Fix docutils rendering (Jelmer Vernooĳ)
- #204, #214: Put files into subdirectory in tarball download (Jelmer Vernooĳ)

1.2.2 (Feb 14, 2018)
-------------------
- #202: Windows encoding problem (Jonas Haag)
- #201: Improve diff rendering (Jonas Haag)

1.2.1 (Jul 5, 2017)
-------------------
- SECURITY ISSUE, PLEASE UPDATE: Fix #200: Missing HTML escaping in diff view
- #189: Submodule info page instead of server error (Jelmer Vernooĳ)
- #187, #191, #165: Bug fixes (Chris St. Pierre, Aleksey Rybalkin)

1.2.0 (Jun 13, 2017)
--------------------
* #177: Fix relative links in READMEs (etc.) (Jelmer Vernooĳ)
* #36: Allow for branch names with ``/``, e.g. ``feature/foobar`` (Martin Zimmermann, Chris St. Pierre)
* #184: Drop support for Python 2.6 (Jelmer Vernooĳ)
* Refactor diff generating code (Jelmer Vernooĳ)
* Fix temporary files not being deleted (Jonas Haag)

1.1.0 (Feb 1, 2017)
-------------------
* Display README on repository landing page (Jelmer Vernooĳ)
* Make all options configurable using environment variables (Jimmy Petersson)
* #122: Support `.git/cloneurl` and `gitweb.url` settings (Jelmer Vernooĳ)
* Support ".mdwn" markdown file extension (Jelmer Vernooĳ)
* #166: Set device viewport (Jonas Haag)
* Fix autoreloader with Python (Jimmy Petersson)
* #169: Fix htdigest with autoreloader (Jimmy Petersson)

1.0.1 (May 24, 2016)
---------------------
* Full support for Python 3 (Louis Sautier, Jonas Haag)

0.9.1 (Apr 14, 2016)
--------------------
* #155: Do not change SCRIPT_NAME if HTTP_X_SCRIPT_NAME isn't set (Louis Sautier)

0.8.0 (Feb 2, 2016)
-------------------
* #140, #145: Deprecate ``klaus.utils.SubUri`` in favor of the new ``klaus.utils.ProxyFix``,
  which correctly handles ``SCRIPT_NAME``. For details on how to use the new ``ProxyFix``,
  see  `Klaus behind a reverse proxy <https://github.com/jonashaag/klaus/wiki/Klaus-behind-a-reverse-proxy>`_.
  (Jelmer Vernooij, Jonas Haag)
* Add man page. (Jelmer Vernooij)
* Add ``--version`` command line option (Jelmer Vernooij)
* Improve error message when ctags is enabled but not installed (Jonas Haag)
* Add a few missing entries to the default robots.txt (Jonas Haag)

0.7.1 (Oct 11, 2015)
--------------------
* Fix #136: wrong .diff URL generated if klaus is mounted under a prefix (John Ko)

0.7.0 (Oct 7, 2015)
-------------------
* Add ctags support (see wiki) (Jonas Haag)
* Append ".diff" or ".patch" to a commit URL and you'll be given a plaintext patch
  (like you can do at GitHub) (Jonas Haag)
* Fix JavaScript line highlighter after window reload (Jonas Haag)

0.6.0 (Aug 6, 2015)
--------------------
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
--------------------
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
