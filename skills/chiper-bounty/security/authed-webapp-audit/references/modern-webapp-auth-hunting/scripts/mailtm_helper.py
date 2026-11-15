#!/usr/bin/env python3
"""mail.tm disposables for authenticated testing: create inbox, fetch OTP, extract links.

Usage:
  from mailtm_helper import new_mailbox, get_otp, get_links
  addr, tok = new_mailbox('qw1')
  otp = get_otp(tok)                 # polls; returns 6-digit code from OTP email
  links = get_links(tok)             # all https links from invite/share emails

Notes:
- Subject format for codes: "Your <site> code is NNNNNN" -> get_otp regex \\d{6}.
- Invite tokens arrive as links in the TEXT body: /app/advisers/accept?token=...,
  /app/shares/accept?token=...
- mail.tm rate-limits account creation (HTTP 429); reuse existing inboxes for retests
  and only create a fresh one when you need a clean invite recipient.
"""
import json, random, re, string, time, urllib.request, urllib.error

BASE = 'https://api.mail.tm'


def new_mailbox(prefix='qw'):
    dom = json.load(urllib.request.urlopen(f'{BASE}/domains', timeout=15))['hydra:member'][0]['domain']
    rnd = prefix + ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    addr = f'{rnd}@{dom}'
    pw = 'QwTest!2026x'
    body = json.dumps({'address': addr, 'password': pw}).encode()
    req = urllib.request.Request(f'{BASE}/accounts', data=body, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as e:
        if e.code != 409:  # 409 = already exists, fine
            print('mail create err', e.code, e.read().decode()[:120])
    req2 = urllib.request.Request(f'{BASE}/token',
                                  data=json.dumps({'address': addr, 'password': pw}).encode(),
                                  headers={'Content-Type': 'application/json'})
    tok = json.load(urllib.request.urlopen(req2, timeout=15))['token']
    return addr, tok


def _messages(tok):
    req = urllib.request.Request(f'{BASE}/messages', headers={'Authorization': f'Bearer {tok}'})
    return json.load(urllib.request.urlopen(req, timeout=15)).get('hydra:member', [])


def _full(tok, mid):
    req = urllib.request.Request(f'{BASE}/messages/{mid}', headers={'Authorization': f'Bearer {tok}'})
    return json.load(urllib.request.urlopen(req, timeout=15))


def get_otp(tok, wait_loops=8, sleep_s=3):
    """Poll inbox, return first 6-digit code found in an email text."""
    for _ in range(wait_loops):
        try:
            for m in _messages(tok):
                full = _full(tok, m['id'])
                mm = re.search(r'\b(\d{6})\b', full.get('text', '') or '')
                if mm:
                    return mm.group(1)
        except Exception as e:
            print('mail err', e)
        time.sleep(sleep_s)
    return None


def get_links(tok, subject_filter=None, wait_loops=6, sleep_s=3):
    """Poll inbox, return list of https URLs (invite/share accept links etc.)."""
    out = []
    for _ in range(wait_loops):
        try:
            for m in _messages(tok):
                subj = m.get('subject', '') or ''
                if subject_filter and subject_filter.lower() not in subj.lower():
                    continue
                full = _full(tok, m['id'])
                out += re.findall(r'https://[^\s">]+', full.get('text', '') or '')
        except Exception as e:
            print('mail err', e)
        if out:
            return out
        time.sleep(sleep_s)
    return out