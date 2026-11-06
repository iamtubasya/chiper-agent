#!/usr/bin/env python3
"""Minimal Chrome CDP driver for authenticated web-app testing.
Connect to a Chrome started with --remote-debugging-port=9222 --remote-allow-origins=*.

Usage:
  from cdp_helper import CDP, totp
  c = CDP(9222)
  c.navigate('https://target/app')
  print(c.js('document.body.innerText.slice(0,500)'))
  print(c.cookie_header())
  body, url, headers = c.capture_post('/app/sources/xxx')   # returns full post body

Key CDP facts learned the hard way:
- --remote-allow-origins=* is REQUIRED or websocket handshake gets 403.
- requestWillBeSent.postData is TRUNCATED; always fetch full body via Network.getRequestPostData.
- document.cookie does NOT show HttpOnly cookies; use Network.getAllCookies.
"""
import json, time, urllib.request, websocket, base64, hmac, hashlib, struct


def totp(secret, period=30, digits=6):
    """RFC 6238 TOTP from a base32 secret (used to enroll MFA without a phone)."""
    key = base64.b32decode(secret + '=' * ((8 - len(secret) % 8) % 8))
    counter = int(time.time() // period)
    msg = struct.pack('>Q', counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    val = struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF
    return str(val % 10 ** digits).zfill(digits)


class CDP:
    def __init__(self, port=9222, pick='quarterwise'):
        d = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json', timeout=10))
        pages = [t for t in d if t['type'] == 'page']
        target = None
        for p in pages:
            if pick in p.get('url', ''):
                target = p
                break
        if not target:
            target = pages[0]
        self.ws = websocket.create_connection(target['webSocketDebuggerUrl'], timeout=40,
                                              header=['Origin: http://localhost'])
        self._mid = 0
        self.posts = {}  # requestId -> request for state-changing captures

    def cmd(self, method, params=None):
        self._mid += 1
        mid = self._mid
        self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get('id') == mid:
                return m.get('result', {})
            if m.get('method') == 'Network.requestWillBeSent':
                p = m['params']
                req = p['request']
                if req['method'] == 'POST' and 'quarterwise' in req['url']:
                    self.posts[p['requestId']] = req

    def enable(self):
        self.cmd('Page.enable')
        self.cmd('Runtime.enable')
        self.cmd('Network.enable')

    def js(self, expr):
        r = self.cmd('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        if 'exceptionDetails' in r:
            return {'err': r['exceptionDetails'].get('text', '')}
        return r.get('result', {}).get('value')

    def navigate(self, url, wait=5):
        self.cmd('Page.navigate', {'url': url})
        time.sleep(wait)

    def cookie_header(self):
        r = self.cmd('Network.getAllCookies')
        return '; '.join(f"{c['name']}={c['value']}" for c in r.get('cookies', [])
                         if 'quarterwise' in c.get('domain', ''))

    def full_post(self, request_id):
        """Full Server Action POST body. Always use this, not req.postData (truncated)."""
        r = self.cmd('Network.getRequestPostData', {'requestId': request_id})
        return r.get('postData', '')

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass