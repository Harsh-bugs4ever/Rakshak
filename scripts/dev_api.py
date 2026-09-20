"""Local demo server using real Lambda handlers and in-memory moto DynamoDB.

Run: python scripts/dev_api.py (requires requirements-dev.txt).
This is a loopback-only development server, not a production web server.
"""
import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=3000)
    args = parser.parse_args()
    os.environ['AWS_ACCESS_KEY_ID'] = 'demo'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'demo'
    os.environ['AWS_DEFAULT_REGION'] = 'ap-south-1'
    os.environ.pop('AWS_ENDPOINT_URL', None)
    from moto import mock_aws
    from scripts import bootstrap
    from src.common import store
    from src.common.response import fail
    from src.handlers import emergency, aftermath, resources, health, ai

    routes = {
        '/emergency/protocols': emergency.handler,
        '/emergency/numbers': emergency.handler,
        '/emergency/good-samaritan': emergency.handler,
        '/aftermath/steps': aftermath.handler,
        '/aftermath/faqs': aftermath.handler,
        '/resources': resources.handler,
        '/health': health.handler,
        '/ai/emergency': ai.handler,
        '/ai/aftermath': ai.handler,
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def do_OPTIONS(self):
            self.respond()

        def respond(self):
            parts = urlsplit(self.path)
            route = routes.get(parts.path.rstrip('/'))
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 0 or length > 16384:
                    self.send_error(413)
                    return
                event = {
                    'path': parts.path, 'httpMethod': self.command,
                    'headers': dict(self.headers),
                    'queryStringParameters': dict(parse_qsl(parts.query)),
                    'body': self.rfile.read(length).decode('utf-8') if length else None,
                }
                response = route(event, None) if route else fail('NOT_FOUND', 'Route not found.', status=404)
            except (ValueError, UnicodeError):
                response = fail('BAD_REQUEST', 'Invalid request body.', status=400)
            self.send_response(response['statusCode'])
            body = response.get('body', '').encode('utf-8')
            for key, value in response['headers'].items():
                self.send_header(key, value)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with mock_aws():
        store.reset_clients()
        for logical in bootstrap.TABLE_SPECS:
            bootstrap.create_table(logical)
            bootstrap.seed_table(logical)
        server = HTTPServer(('127.0.0.1', args.port), Handler)
        print(f'Demo API ready at http://127.0.0.1:{args.port}; data resets on exit.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            store.reset_clients()


if __name__ == '__main__':
    main()
