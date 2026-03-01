"""
MacBook Proxy Server

Provides residential IP access for AI agents by relaying requests through
your MacBook's network connection.

Your MacBook's residential IP bypasses most bot protection (Cloudflare,
Kasada, DataDome, etc.) because it looks like a real user.

This server acts as a proxy relay:
    Agent -> (internet) -> MacBook Server -> (residential IP) -> Target Site

Usage:
    # On your MacBook:
    pip install flask requests
    export PROXY_API_KEY="your-secret-key"
    python macbook_server.py

    # Configure the agent (env vars):
    MACBOOK_PROXY_URL=http://<your-macbook-ip>:8888
    MACBOOK_API_KEY=your-secret-key

Security:
    - API key authentication on all endpoints
    - Only accepts requests with valid X-API-Key header
    - Bind to 0.0.0.0 only if behind a firewall/VPN

Port Forwarding (if behind NAT):
    Option A: Use ngrok (easiest)
        ngrok http 8888
        -> Use the ngrok URL as MACBOOK_PROXY_URL

    Option B: Tailscale (recommended for security)
        Install Tailscale on both machines
        -> Use Tailscale IP as MACBOOK_PROXY_URL

    Option C: Port forward 8888 on your router
        -> Use your public IP as MACBOOK_PROXY_URL
"""

import os
import sys
import logging
from datetime import datetime

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("Flask not installed. Run: pip install flask requests")
    sys.exit(1)

import requests as req_lib

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

API_KEY = os.getenv('PROXY_API_KEY')
if not API_KEY:
    raise RuntimeError("PROXY_API_KEY environment variable is required. Set it before starting the server.")
BIND_HOST = os.getenv('PROXY_BIND_HOST', '0.0.0.0')
BIND_PORT = int(os.getenv('PROXY_BIND_PORT', '8888'))


def require_api_key(f):
    """Decorator to enforce API key authentication."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key', '')
        if key != API_KEY:
            logger.warning(f"Unauthorized request from {request.remote_addr}")
            return jsonify({'error': 'unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint (no auth required)."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'server': 'macbook-proxy',
    })


@app.route('/proxy', methods=['POST'])
@require_api_key
def proxy_request():
    """
    Generic proxy endpoint.
    Accepts JSON with target URL and forwards the request from this MacBook's IP.

    Request body:
        {
            "url": "https://example.com/api/data",
            "method": "GET",          # GET, POST, PUT, DELETE
            "headers": {},            # Optional headers to forward
            "params": {},             # Optional query parameters
            "json_body": {}           # Optional JSON body (for POST/PUT)
        }

    Response:
        The raw response from the target URL, with status code preserved.
    """
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'url required in JSON body'}), 400

    target_url = data['url']
    method = data.get('method', 'GET').upper()
    headers = data.get('headers') or {}
    params = data.get('params')
    json_body = data.get('json_body')
    timeout = data.get('timeout', 30)

    # Remove proxy-specific headers that shouldn't be forwarded
    headers.pop('X-API-Key', None)
    headers.pop('Host', None)

    logger.info(f"Proxying {method} {target_url[:80]}")

    try:
        resp = req_lib.request(
            method=method,
            url=target_url,
            headers=headers,
            params=params,
            json=json_body,
            timeout=timeout,
            allow_redirects=True,
        )

        # Return response with original status code and content type
        content_type = resp.headers.get('Content-Type', 'application/json')

        if 'application/json' in content_type:
            try:
                return jsonify(resp.json()), resp.status_code
            except ValueError:
                pass

        return resp.text, resp.status_code, {'Content-Type': content_type}

    except req_lib.Timeout:
        logger.error(f"Timeout proxying {target_url[:80]}")
        return jsonify({'error': 'upstream_timeout'}), 504
    except req_lib.ConnectionError as e:
        logger.error(f"Connection error proxying {target_url[:80]}: {e}")
        return jsonify({'error': 'upstream_connection_error'}), 502
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/batch', methods=['POST'])
@require_api_key
def proxy_batch():
    """
    Batch proxy endpoint - send multiple requests in one call.

    Request body:
        {
            "requests": [
                {"url": "https://example.com/1", "method": "GET"},
                {"url": "https://example.com/2", "method": "GET"},
            ]
        }

    Response:
        {"results": [{"status": 200, "data": {...}}, ...]}
    """
    data = request.get_json()
    if not data or 'requests' not in data:
        return jsonify({'error': 'requests array required'}), 400

    results = []
    for req_spec in data['requests'][:20]:  # Max 20 per batch
        target_url = req_spec.get('url', '')
        method = req_spec.get('method', 'GET').upper()
        headers = req_spec.get('headers') or {}
        params = req_spec.get('params')
        json_body = req_spec.get('json_body')

        try:
            resp = req_lib.request(
                method=method,
                url=target_url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=req_spec.get('timeout', 15),
            )

            try:
                body = resp.json()
            except ValueError:
                body = resp.text

            results.append({
                'url': target_url,
                'status': resp.status_code,
                'data': body,
            })
        except Exception as e:
            results.append({
                'url': target_url,
                'status': 0,
                'error': str(e),
            })

    return jsonify({'results': results})


if __name__ == '__main__':
    logger.info(f"Starting MacBook Proxy Server on {BIND_HOST}:{BIND_PORT}")
    logger.info(f"Health check: http://localhost:{BIND_PORT}/health")
    logger.info(f"Proxy endpoint: POST http://localhost:{BIND_PORT}/proxy")

    app.run(host=BIND_HOST, port=BIND_PORT, debug=False)
