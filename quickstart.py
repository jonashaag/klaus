#!/usr/bin/env python2
# coding: utf-8
import sys, os
import argparse

try:
    import nano
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'nano'))
    try:
        import nano
    except ImportError:
        raise ImportError(
            "Could not find a copy of nano (https://github.com/jonashaag/nano). "
            "Use 'git submodule update --init' to initialize the nano submodule "
            "or copy the 'nano.py' into the klaus root directory by hand."
        )

try:
    from bjoern import run
except ImportError:
    from wsgiref.simple_server import make_server
    def run(app, host, port):
        make_server(host, port, app).serve_forever()

def valid_directory(path):
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError('%r: No such directory' % path)
    return path

def main():
    parser = argparse.ArgumentParser(epilog='Gemüse kaufen!')
    parser.add_argument('host', help='(without http://)')
    parser.add_argument('port', type=int)
    parser.add_argument('--display-host', dest='custom_host')
    parser.add_argument('repo', nargs='+', type=valid_directory,
                        help='repository directories to serve')
    args = parser.parse_args()

    from klaus import app
    if args.custom_host:
        app.custom_host = args.custom_host

    run(app, args.host, args.port)

if __name__ == '__main__':
    main()
