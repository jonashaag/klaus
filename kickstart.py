#!/usr/bin/env python2
import os
import sys

from klaus import app
app.repos = {repo.rstrip(os.sep).split(os.sep)[-1] : repo
             for repo in sys.argv[1:]}

import bjoern
bjoern.run(app, '127.0.0.1', 8080)
