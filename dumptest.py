""" Very dump testing tool: Ensures all sites respond with HTTP 2xx/3xx """
import re
import httplib
from collections import defaultdict

AHREF_RE = re.compile('href="([^"]+)"')

BASE_URL = 'http://localhost:8080'

errors = defaultdict(set)
urls = {'/'}
while urls:
    try:
        http_conn.close()
    except NameError:
        pass
    http_conn = httplib.HTTPConnection('localhost', 8080)
    url = urls.pop()
    print 'Requesting %r...' % url
    http_conn.request('GET', BASE_URL + url)
    response = http_conn.getresponse()
    status = str(response.status)
    if status[0] == '3':
        urls.add(response.getheader('Location'))
    elif status[0] == '2':
        urls.update(AHREF_RE.findall(response.read()))
    else:
        errors[status].add(url)

print errors
