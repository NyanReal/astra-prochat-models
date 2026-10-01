#!/usr/bin/env python3
"""Serve this package without any dependencies. Ctrl-C stops the server.
Default: loopback only. --lan explicitly exposes this folder to your network.
"""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent

class AssetHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      '.glb': 'model/gltf-binary', '.js': 'text/javascript',
                      '.css': 'text/css', '.mp4': 'video/mp4'}

def make_server(host: str = '127.0.0.1', port: int = 8000) -> ThreadingHTTPServer:
    """Bind a read-only static server to this package, not the working directory."""
    if not 0 <= port <= 65535:
        raise ValueError('Port must be between 0 and 65535.')
    return ThreadingHTTPServer((host, port), partial(AssetHandler, directory=str(ROOT)))

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-open', action='store_true', help='Do not open the browser automatically.')
    parser.add_argument('--lan', action='store_true', help='Expose this package on your local network (0.0.0.0).')
    args = parser.parse_args()
    try:
        server = make_server('0.0.0.0' if args.lan else '127.0.0.1', args.port)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Cannot start preview: {error}\nTry a different --port.\n')
    port = server.server_address[1]
    url = f'http://127.0.0.1:{port}/preview/index.html'
    print(f'HOPPER 03 preview: {url}', flush=True)
    if args.lan:
        print(f'LAN enabled. On another device: http://<this-computer-LAN-IP>:{port}/preview/index.html', flush=True)
        print('Every file in this package is readable from your network until you stop this server.', flush=True)
    print('Press Ctrl-C to stop.', flush=True)
    if not args.no_open:
        threading.Timer(.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping preview.')
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
