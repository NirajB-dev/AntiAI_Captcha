#Author: Pravigya


#!/usr/bin/env python3
"""
Simple Python Load Balancer for Anti-AI CAPTCHA System
Round-robin load balancing between multiple backend servers.
No external dependencies (uses only stdlib).

Usage:
    python load_balancer.py [--port 8080] [--backends "host1:port1,host2:port2"]

Example:
    python load_balancer.py --port 8080 --backends "pi1.local:5001,pi2.local:5001"
"""

import http.server
import urllib.request
import urllib.error
import argparse
import threading
import json
import time
import sys
from urllib.parse import urlparse, urljoin


class LoadBalancer(http.server.BaseHTTPRequestHandler):
    """Simple round-robin load balancer."""

    # Class-level configuration (set in main)
    backends = []
    current_backend_idx = 0
    backend_lock = threading.Lock()
    backend_health = {}  # {backend_url: {"healthy": bool, "last_check": time}}

    @classmethod
    def get_next_backend(cls):
        """Get next healthy backend using round-robin."""
        with cls.backend_lock:
            # Try to find a healthy backend
            attempts = len(cls.backends)
            for _ in range(attempts):
                backend = cls.backends[cls.current_backend_idx]
                cls.current_backend_idx = (cls.current_backend_idx + 1) % len(cls.backends)

                # Check if backend is healthy (with caching)
                health = cls.backend_health.get(backend, {"healthy": True, "last_check": 0})
                if time.time() - health["last_check"] > 10:  # Re-check every 10 seconds
                    health["healthy"] = cls.check_backend_health(backend)
                    health["last_check"] = time.time()
                    cls.backend_health[backend] = health

                if health["healthy"]:
                    return backend

            # All backends unhealthy, try the first one anyway
            return cls.backends[0] if cls.backends else None

    @classmethod
    def check_backend_health(cls, backend_url):
        """Check if a backend is healthy."""
        try:
            req = urllib.request.Request(f"{backend_url}/health", method='GET')
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200
        except:
            return False

    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[{time.strftime('%H:%M:%S')}] {self.address_string()} - {args[0]}")

    def do_request(self, method):
        """Forward request to backend."""
        backend = self.get_next_backend()
        if not backend:
            self.send_error(503, "No healthy backends available")
            return

        # Build target URL
        target_url = urljoin(backend, self.path)

        # Read request body if present
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Build headers (exclude hop-by-hop headers)
        headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in ['host', 'connection', 'keep-alive', 'transfer-encoding']
        }
        headers['X-Forwarded-For'] = self.client_address[0]
        headers['X-Load-Balancer'] = 'anti-ai-captcha-lb'

        try:
            # Create request
            req = urllib.request.Request(
                target_url,
                data=body,
                headers=headers,
                method=method
            )

            # Send request
            with urllib.request.urlopen(req, timeout=30) as response:
                # Forward response status
                self.send_response(response.status)

                # Forward response headers
                for header, value in response.getheaders():
                    if header.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(header, value)
                self.send_header('X-Backend', backend)
                self.end_headers()

                # Forward response body
                self.wfile.write(response.read())

        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())

        except urllib.error.URLError as e:
            # Mark backend as unhealthy
            self.backend_health[backend] = {"healthy": False, "last_check": time.time()}
            print(f"Backend {backend} failed: {e}")

            # Retry with another backend
            retry_backend = self.get_next_backend()
            if retry_backend and retry_backend != backend:
                print(f"Retrying with {retry_backend}")
                self.path = self.path  # Keep original path
                self.do_request(method)
            else:
                self.send_error(502, f"Backend error: {e}")

        except Exception as e:
            self.send_error(500, f"Load balancer error: {e}")

    def do_GET(self):
        self.do_request('GET')

    def do_POST(self):
        self.do_request('POST')

    def do_PUT(self):
        self.do_request('PUT')

    def do_DELETE(self):
        self.do_request('DELETE')

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


class ThreadedHTTPServer(http.server.HTTPServer):
    """Handle requests in separate threads."""
    allow_reuse_address = True

    def process_request(self, request, client_address):
        thread = threading.Thread(target=self._process_request_thread, args=(request, client_address))
        thread.daemon = True
        thread.start()

    def _process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          ANTI-AI CAPTCHA - PYTHON LOAD BALANCER                  ║
║                                                                  ║
║  Simple round-robin load balancing with health checks            ║
║  No external dependencies required                               ║
╚══════════════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(description='Simple Python Load Balancer')
    parser.add_argument('--port', type=int, default=8080, help='Load balancer port (default: 8080)')
    parser.add_argument('--backends', type=str, default='localhost:5001',
                        help='Comma-separated backend URLs (default: localhost:5001)')
    args = parser.parse_args()

    # Parse backends
    backends = []
    for backend in args.backends.split(','):
        backend = backend.strip()
        if not backend.startswith('http'):
            backend = f'http://{backend}'
        backends.append(backend)

    if not backends:
        print("Error: No backends specified")
        sys.exit(1)

    # Configure load balancer
    LoadBalancer.backends = backends

    print_banner()
    print(f"Load Balancer Port: {args.port}")
    print(f"Backends: {', '.join(backends)}")
    print()

    # Check initial backend health
    print("Checking backend health...")
    for backend in backends:
        healthy = LoadBalancer.check_backend_health(backend)
        LoadBalancer.backend_health[backend] = {"healthy": healthy, "last_check": time.time()}
        status = "✅ HEALTHY" if healthy else "❌ UNHEALTHY"
        print(f"  {backend}: {status}")

    print()
    print(f"Starting load balancer on http://0.0.0.0:{args.port}")
    print("Press Ctrl+C to stop\n")

    try:
        server = ThreadedHTTPServer(('0.0.0.0', args.port), LoadBalancer)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down load balancer...")
        server.shutdown()


if __name__ == '__main__':
    main()
