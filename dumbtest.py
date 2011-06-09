""" Very dumb testing tool: Ensures all sites respond with HTTP 2xx/3xx """
import sys
import re
import time
import httplib
from collections import defaultdict
import atexit

def view_from_url(url):
    try:
        return url.split('/')[2]
    except IndexError:
        return url

AHREF_RE = re.compile('href="([\w/][^"]+)"')

BASE_URL = 'http://localhost:8080'

seen = set()
errors = defaultdict(set)
durations = defaultdict(list)

def main():
    urls = {'/'}
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
        if url.startswith('http'):
            continue
        if '-v' in sys.argv:
            print 'Requesting %r...' % url
        start = time.time()
        http_conn.request('GET', BASE_URL + url)
        response = http_conn.getresponse()
        durations[view_from_url(url)].append(time.time() - start)
        status = str(response.status)
        if status[0] == '3':
            urls.add(response.getheader('Location'))
        elif status[0] == '2':
            urls.update(AHREF_RE.findall(response.read()))
        else:
            errors[status].add(url)

def print_stats():
    print len(seen)
    print errors
    print {url: sum(times)/len(times) for url, times in durations.iteritems()}
atexit.register(print_stats)

main()
