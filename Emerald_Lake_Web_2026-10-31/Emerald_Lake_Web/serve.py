#!/usr/bin/env python3
"""Serve the bundled static scene on localhost; standard Python only."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse
import threading
import webbrowser

def main():
    parser=argparse.ArgumentParser(description='Open Emerald Lake locally')
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    directory=Path(__file__).resolve().parent/'dist'
    if not (directory/'index.html').is_file():
        raise SystemExit('dist/index.html was not found. Extract the entire ZIP first.')
    handler=partial(SimpleHTTPRequestHandler,directory=str(directory))
    try:
        server=ThreadingHTTPServer(('127.0.0.1',args.port),handler)
    except OSError as error:
        raise SystemExit(f'Port {args.port} is unavailable. Try: python serve.py --port 8001\n{error}')
    url=f'http://127.0.0.1:{args.port}/'
    print(f'Emerald Lake: {url}\nPress Ctrl+C to stop.')
    if not args.no_browser:
        threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
