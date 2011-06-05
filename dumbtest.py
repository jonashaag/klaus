""" Very dumb testing tool: Ensures all sites respond with HTTP 2xx/3xx """
from __future__ import print_function
import sys
import re
import httplib
from collections import defaultdict
import atexit

AHREF_RE = re.compile('href="([\w/][^"]+)"')

BASE_URL = 'http://localhost:8080'

errors = defaultdict(set)
atexit.register(lambda: print(errors))

urls = {'/'}
seen = set()
while urls:
    try:
        http_conn.close()
    except NameError:
        pass
    http_conn = httplib.HTTPConnection('localhost', 8080)
    url = urls.pop()
    if url in seen:
        continue
    seen.add(url)
    if '-v' in sys.argv:
        print('Requesting %r...' % url)
    http_conn.request('GET', BASE_URL + url)
    response = http_conn.getresponse()
    status = str(response.status)
    if status[0] == '3':
        urls.add(response.getheader('Location'))
    elif status[0] == '2':
        urls.update(AHREF_RE.findall(response.read()))
    else:
        errors[status].add(url)
