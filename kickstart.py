#!/usr/bin/env python2
import os
import sys
import inspect

class ReloadApplicationMiddleware(object):
    def __init__(self, import_func):
        self.import_func = import_func
        self.app = import_func()
        self.files = self.get_module_mtimes()

    def get_module_mtimes(self):
        files = {}
        for module in sys.modules.itervalues():
            try:
                file = inspect.getsourcefile(module)
                files[file] = os.stat(file).st_mtime
            except TypeError:
                continue
        return files

    def shall_reload(self):
        for file, mtime in self.get_module_mtimes().iteritems():
            if not file in self.files or self.files[file] < mtime:
                self.files = self.get_module_mtimes()
                return True
        return False

    def __call__(self, *args, **kwargs):
        if self.shall_reload():
            print 'Reloading...'
            self.app = self.import_func()
        return self.app(*args, **kwargs)

def import_app():
    sys.modules.pop('klaus', None)
    from klaus import app
    app.repos = {repo.rstrip(os.sep).split(os.sep)[-1] : repo
                 for repo in sys.argv[1:]}
    return app

import bjoern
bjoern.run(ReloadApplicationMiddleware(import_app), '127.0.0.1', 8080)
