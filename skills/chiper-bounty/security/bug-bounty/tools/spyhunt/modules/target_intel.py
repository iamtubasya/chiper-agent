"""
Target Intelligence Module for SpyHunt
Analyzes domains/URLs and provides pentest suggestions with elegant output.
"""

import re
import socket
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from urllib.parse import urlparse
from typing import Optional, List, Dict, Tuple

# Timeout for network ops - skip and move on if no response
NETWORK_TIMEOUT = 7

# Industry inference patterns: (pattern, industry, description)
INDUSTRY_PATTERNS = [
    (r'\b(pay|payment|paypal|stripe|checkout|billing|invoice|finance)\b', 'Fintech / Payments', 'Payment processing, billing, financial services'),
    (r'\b(health|medical|hospital|pharma|patient|clinical)\b', 'Healthcare', 'Medical, pharmaceutical, patient data'),
    (r'\b(retail|shop|store|ecommerce|cart|product)\b', 'E-commerce / Retail', 'Online shopping, product catalogs'),
    (r'\b(api|gateway|service|microservice)\b', 'API / Backend', 'REST/GraphQL APIs, microservices'),
    (r'\b(admin|dashboard|manage|panel|control)\b', 'Admin / Management', 'Administrative interfaces'),
    (r'\b(dev|staging|stage|qa|test|uat|preprod)\b', 'Development / Staging', 'Non-production environments'),
    (r'\b(auth|login|sso|identity|oauth)\b', 'Authentication', 'Login, SSO, identity providers'),
    (r'\b(cdn|static|assets|media)\b', 'CDN / Assets', 'Content delivery, static assets'),
    (r'\b(mail|email|smtp)\b', 'Email', 'Email services'),
    (r'\b(mobile|app|ios|android)\b', 'Mobile', 'Mobile app backends'),
    (r'\b(cloud|aws|azure|gcp)\b', 'Cloud', 'Cloud infrastructure'),
    (r'\b(gov|government)\b', 'Government', 'Government services'),
    (r'\b(edu|education|university)\b', 'Education', 'Educational institutions'),
    (r'\b(telco|telecom|cellular|mobile)\b', 'Telecommunications', 'Telecom providers'),
]

# Subdomain -> pentest focus mapping
SUBDOMAIN_FOCUS = {
    'api': ['IDOR', 'Auth bypass', 'Rate limiting', 'Mass assignment', 'GraphQL introspection'],
    'admin': ['Default creds', 'Auth bypass', 'Privilege escalation', 'Session fixation'],
    'dev': ['Exposed debug', 'Source maps', '.env files', 'Swagger/OpenAPI'],
    'staging': ['Weak auth', 'Test data exposure', 'Debug endpoints', 'Config leaks'],
    'test': ['Test accounts', 'Debug mode', 'Sensitive data in responses'],
    'uat': ['Test data', 'Weak security controls'],
    'beta': ['Early access bugs', 'Incomplete validation'],
    'internal': ['IP restriction bypass', 'VPN requirements'],
    'vpn': ['Auth bypass', 'Credential stuffing'],
    'mail': ['Email header injection', 'Open relay', 'Phishing vectors'],
    'cdn': ['Cache poisoning', 'Origin confusion', 'Subdomain takeover'],
    'static': ['Sensitive files', 'Source maps', 'Config in JS'],
    'graphql': ['Introspection', 'IDOR', 'DoS', 'Auth bypass'],
    'auth': ['OAuth misconfig', 'JWT issues', 'Session fixation'],
    'sso': ['Open redirect', 'Token leakage', 'IdP misconfig'],
    'payment': ['PCI scope', 'Card data', 'Webhook validation'],
    'webhook': ['SSRF', 'Replay attacks', 'Signature bypass'],
}

# TLD hints
TLD_HINTS = {
    '.gov': 'Government - strict scope, compliance focus',
    '.gov.uk': 'UK Government',
    '.edu': 'Education - student data, research',
    '.mil': 'Military - out of scope for most programs',
    '.au': 'Australian entity',
    '.co.uk': 'UK commercial',
    '.com.au': 'Australian commercial',
    '.de': 'German entity',
    '.fr': 'French entity',
    '.jp': 'Japanese entity',
}

# Industry-specific pentest suggestions (only used when industry matches)
INDUSTRY_PENTEST = {
    'fintech': [
        'Payment amount/currency manipulation',
        'Webhook signature bypass',
        'Account takeover via IDOR on transfers',
        'PII/card data exposure in API responses',
    ],
    'healthcare': [
        'PHI/PII exposure in patient endpoints',
        'HIPAA scope - medical record IDOR',
        'Appointment/booking logic flaws',
        'Lab results or prescription access',
    ],
    'ecommerce': [
        'Price/quantity manipulation at checkout',
        'Coupon/discount stacking abuse',
        'Inventory or order IDOR',
        'Gift card balance manipulation',
    ],
    'api': [
        'GraphQL introspection (/graphql)',
        'Swagger/OpenAPI at /api-docs, /swagger',
        'Mass assignment on POST/PUT',
        'JWT alg:none or weak secret',
        'API version auth differences (v1 vs v2)',
    ],
    'auth': [
        'OAuth redirect_uri open redirect',
        'JWT token manipulation',
        'Password reset token predictability',
        '2FA/MFA bypass or bypass codes',
    ],
    'staging': [
        'Default/test credentials',
        'Debug endpoints, .env, config leaks',
        'Test data with real PII',
        'Weaker WAF or missing auth',
    ],
    'admin': [
        'Default admin credentials',
        'Privilege escalation paths',
        'Session fixation on admin login',
        'Audit log bypass or tampering',
    ],
    'cdn': [
        'Cache poisoning via headers',
        'Origin confusion / host override',
        'Subdomain takeover (dangling CNAME)',
    ],
    'email': [
        'Email header injection',
        'Open relay / SMTP auth bypass',
        'Phishing via spoofed sender',
    ],
    'gov': [
        'Citizen data IDOR',
        'Document/FOIA endpoint exposure',
        'Voter or license data access',
    ],
    'edu': [
        'Student/grade data IDOR',
        'Course enrollment logic',
        'Research data exposure',
    ],
    'telco': [
        'SIM swap / account takeover',
        'Phone number enumeration',
        'Billing or plan manipulation',
    ],
}

# Domain/company name patterns -> what they likely do
DOMAIN_PURPOSE = [
    (r'\b(paypal|stripe|square|braintree|adyen)\b', 'Payment processor', 'fintech'),
    (r'\b(github|gitlab|bitbucket)\b', 'Developer platform', 'api'),
    (r'\b(aws|azure|gcp|cloudflare)\b', 'Cloud provider', 'api'),
    (r'\b(slack|discord|teams)\b', 'Collaboration/messaging', 'auth'),
    (r'\b(shopify|woocommerce|bigcommerce)\b', 'E-commerce platform', 'ecommerce'),
    (r'\b(salesforce|hubspot|zendesk)\b', 'CRM/support', 'api'),
    (r'\b(okta|auth0|ping)\b', 'Identity provider', 'auth'),
    (r'\b(twilio|sendgrid|mailgun)\b', 'Communications API', 'api'),
    (r'\b(vercel|netlify)\b', 'Hosting/CDN', 'cdn'),
]


def extract_domain(url_or_domain: str) -> str:
    """Extract clean domain from URL or domain string."""
    s = url_or_domain.strip().lower()
    if not s:
        return ''
    if '://' in s:
        parsed = urlparse(s if s.startswith('http') else f'https://{s}')
        return parsed.netloc or parsed.path.split('/')[0]
    return s.split('/')[0].split(':')[0]


def get_whois_info(domain: str, timeout: int = NETWORK_TIMEOUT) -> Dict:
    """Get WHOIS data for domain. Skips on timeout."""
    def _whois_lookup():
        import whois
        w = whois.whois(domain)
        return {
            'org': getattr(w, 'org', None) or getattr(w, 'registrant_org', None),
            'registrar': getattr(w, 'registrar', None),
            'creation_date': str(w.creation_date[0]) if isinstance(getattr(w, 'creation_date'), list) else str(getattr(w, 'creation_date', '')),
            'country': getattr(w, 'country', None),
            'name_servers': getattr(w, 'name_servers', None),
        }
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_whois_lookup)
            return future.result(timeout=timeout)
    except (FuturesTimeoutError, Exception):
        return {}


def fetch_page_info(url: str, timeout: int = NETWORK_TIMEOUT) -> Dict:
    """Fetch title, meta, and headers from URL."""
    try:
        import requests
        from bs4 import BeautifulSoup
        if not url.startswith('http'):
            url = f'https://{url}'
        r = requests.get(url, timeout=timeout, verify=False, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.find('title')
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        return {
            'status': r.status_code,
            'title': title.get_text().strip()[:80] if title else None,
            'description': (meta_desc.get('content') or '')[:120] if meta_desc else None,
            'server': r.headers.get('Server'),
            'x_powered': r.headers.get('X-Powered-By'),
            'content_type': r.headers.get('Content-Type', '')[:50],
        }
    except Exception:
        return {}


def infer_industry(domain: str, title: str = '', description: str = '') -> List[Tuple[str, str]]:
    """Infer industry from domain, title, description."""
    text = f'{domain} {title} {description}'.lower()
    matches = []
    for pattern, industry, desc in INDUSTRY_PATTERNS:
        if re.search(pattern, text):
            matches.append((industry, desc))
    return matches[:5]  # Top 5


def get_subdomain_hints(domain: str) -> List[Tuple[str, List[str]]]:
    """Get pentest focus based on subdomain."""
    parts = domain.split('.')
    if len(parts) < 3:
        return []
    sub = parts[0].lower()
    for key, focus in SUBDOMAIN_FOCUS.items():
        if key in sub:
            return [(sub, focus)]
    return []


def get_tld_hint(domain: str) -> Optional[str]:
    """Get TLD-based hint."""
    for tld, hint in TLD_HINTS.items():
        if domain.lower().endswith(tld):
            return hint
    return None


def infer_domain_purpose(domain: str, org: str = '', title: str = '') -> Tuple[Optional[str], Optional[str]]:
    """Infer what the domain/company does from name patterns. Returns (description, industry_key)."""
    text = f'{domain} {org} {title}'.lower()
    for pattern, desc, key in DOMAIN_PURPOSE:
        if re.search(pattern, text):
            return (desc, key)
    return (None, None)


def get_suggestions(
    domain: str,
    industry_matches: List[Tuple[str, str]],
    subdomain_focus: List,
    tld_hint: Optional[str],
    org: str = '',
    title: str = '',
) -> Dict[str, List[str]]:
    """Build pentest suggestions based on domain, company, and inferred purpose."""
    suggestions = {'search': [], 'pentest': [], 'other': []}

    # 1. Domain/company purpose (e.g., paypal -> fintech, github -> api)
    purpose_desc, purpose_key = infer_domain_purpose(domain, org, title)
    if purpose_key and purpose_key in INDUSTRY_PENTEST:
        suggestions['pentest'].extend(INDUSTRY_PENTEST[purpose_key])
        if purpose_desc:
            suggestions['other'].insert(0, f'Likely: {purpose_desc}')

    # 2. Industry from domain/title patterns
    industry_keys = set()
    for ind, _ in industry_matches:
        if 'API' in ind or 'Backend' in ind:
            industry_keys.add('api')
        elif 'Auth' in ind:
            industry_keys.add('auth')
        elif 'Fintech' in ind or 'Payment' in ind:
            industry_keys.add('fintech')
        elif 'E-commerce' in ind or 'Retail' in ind:
            industry_keys.add('ecommerce')
        elif 'Development' in ind or 'Staging' in ind:
            industry_keys.add('staging')
        elif 'Admin' in ind:
            industry_keys.add('admin')
        elif 'CDN' in ind:
            industry_keys.add('cdn')
        elif 'Email' in ind:
            industry_keys.add('email')
        elif 'Government' in ind:
            industry_keys.add('gov')
        elif 'Education' in ind:
            industry_keys.add('edu')
        elif 'Telecom' in ind:
            industry_keys.add('telco')
        elif 'Healthcare' in ind:
            industry_keys.add('healthcare')

    for key in industry_keys:
        if key in INDUSTRY_PENTEST and key != purpose_key:  # avoid duplicate if already from purpose
            suggestions['pentest'].extend(INDUSTRY_PENTEST[key])

    # 3. Subdomain-specific (highest priority - very targeted)
    for sub, focus in subdomain_focus:
        suggestions['pentest'] = focus + suggestions['pentest']  # prepend, most relevant
        suggestions['search'].append(f'site:{domain} inurl:{sub}')

    # 4. TLD hint
    if tld_hint:
        suggestions['other'].append(f'TLD: {tld_hint}')

    # 5. Search suggestions based on what we found
    if not suggestions['search']:
        suggestions['search'] = [
            f'site:{domain} filetype:pdf',
            f'site:{domain} inurl:api OR inurl:admin',
            f'site:{domain} "api_key" OR "secret" OR "password"',
        ]

    # 6. Fallback: if nothing matched, give minimal generic recon
    if not suggestions['pentest']:
        suggestions['pentest'] = [
            'Subdomain enum + wayback URLs (recon first)',
            'Check for exposed swagger, graphql, actuator',
            'IDOR on any object IDs in URLs/APIs',
        ]

    # Deduplicate while preserving order
    seen = set()
    for k in suggestions:
        suggestions[k] = [x for x in suggestions[k] if x not in seen and not seen.add(x)]

    return suggestions


def resolve_ip(domain: str, timeout: int = NETWORK_TIMEOUT) -> Optional[str]:
    """Resolve domain to IP. Skips on timeout."""
    def _resolve():
        return socket.gethostbyname(domain)
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_resolve)
            return future.result(timeout=timeout)
    except (FuturesTimeoutError, Exception):
        return None


def analyze_target(url_or_domain: str) -> Dict:
    """Full analysis of a single target."""
    domain = extract_domain(url_or_domain)
    if not domain:
        return {'error': 'Invalid domain'}

    whois_data = get_whois_info(domain)
    page_info = fetch_page_info(domain)
    industry = infer_industry(domain, page_info.get('title') or '', page_info.get('description') or '')
    subdomain_focus = get_subdomain_hints(domain)
    tld_hint = get_tld_hint(domain)
    org = str(whois_data.get('org', '') or '')
    title = str(page_info.get('title', '') or '')
    suggestions = get_suggestions(domain, industry, subdomain_focus, tld_hint, org=org, title=title)
    ip = resolve_ip(domain)

    return {
        'domain': domain,
        'url': url_or_domain,
        'ip': ip,
        'whois': whois_data,
        'page': page_info,
        'industry': industry,
        'subdomain_focus': subdomain_focus,
        'tld_hint': tld_hint,
        'suggestions': suggestions,
    }


def format_output(data: Dict, use_color: bool = True) -> str:
    """Format analysis as beautiful CLI output."""
    from colorama import Fore, Style, init
    init(autoreset=True)

    C = Fore.CYAN
    G = Fore.GREEN
    Y = Fore.YELLOW
    M = Fore.MAGENTA
    W = Fore.WHITE
    R = Fore.RED
    B = Fore.BLUE
    DIM = Style.DIM
    BOLD = Style.BRIGHT
    RST = Style.RESET_ALL

    if not use_color:
        C = G = Y = M = W = R = B = DIM = BOLD = RST = ''

    lines = []

    def section(title: str):
        return f"\n  {BOLD}{C}{title}{RST}"

    def item(label: str, value: str):
        if not value:
            return ''
        return f"  {Y}{label:16}{RST} {W}{value}{RST}"

    def bullet(text: str):
        return f"  {G}•{RST} {text}"

    if 'error' in data:
        return f"{R}[!] {data['error']}{RST}"

    d = data['domain']
    w = data.get('whois', {})
    p = data.get('page', {})
    ind = data.get('industry', [])
    sub = data.get('subdomain_focus', [])
    sug = data.get('suggestions', {})
    tld = data.get('tld_hint')

    lines.append(f"\n  {BOLD}{M}TARGET INTELLIGENCE{RST}  {DIM}·{RST}  {C}{d}{RST}")
    if data.get('ip'):
        lines.append(f"  {DIM}IP{RST}  {data['ip']}{RST}")

    # What is this domain?
    lines.append(section("WHAT IS THIS DOMAIN?"))
    if w.get('org'):
        lines.append(item("Organization", str(w['org'])[:50]))
    if w.get('registrar'):
        lines.append(item("Registrar", str(w['registrar'])[:50]))
    if w.get('country'):
        lines.append(item("Country", str(w['country'])))
    if p.get('title'):
        lines.append(item("Page Title", (p['title'] or '')[:55]))
    if p.get('description'):
        desc = (p.get('description') or '')[:55] + ('...' if len(p.get('description', '')) > 55 else '')
        lines.append(item("Description", desc))
    if p.get('server'):
        lines.append(item("Server", p['server']))
    if p.get('x_powered'):
        lines.append(item("X-Powered-By", p['x_powered']))
    if p.get('status'):
        lines.append(item("HTTP Status", str(p['status'])))
    if ind:
        lines.append(item("Industry", ind[0][0]))
        for _, desc in ind[1:2]:
            lines.append(f"  {DIM}  → {desc[:55]}{RST}")
    if tld:
        lines.append(item("TLD Note", tld[:55]))

    # What to search for
    lines.append(section("WHAT TO SEARCH FOR"))
    search_items = sug.get('search', [])
    if not search_items:
        search_items = [
            f'site:{d} filetype:pdf',
            f'site:{d} inurl:admin',
            f'site:{d} inurl:api',
            f'site:{d} "api_key" OR "apikey" OR "secret"',
        ]
    for s in search_items[:8]:
        lines.append(bullet(s))

    # What to pentest
    lines.append(section("PENTEST SUGGESTIONS"))
    for pt in sug.get('pentest', [])[:12]:
        lines.append(bullet(pt))

    # Subdomain-specific
    if sub:
        lines.append(f"\n  {BOLD}{B}Subdomain focus{RST}")
        for subname, focus in sub:
            lines.append(f"  {B}{subname}{RST}  →  {', '.join(focus[:4])}")

    # Other notes
    if sug.get('other'):
        for o in sug['other']:
            lines.append(bullet(o))

    lines.append("")
    return '\n'.join(lines)


def data_to_graph(data: Dict) -> tuple:
    """Convert analysis data to graph nodes and edges for vis.js."""
    if 'error' in data:
        return [], []

    d = data['domain']
    w = data.get('whois', {})
    p = data.get('page', {})
    ind = data.get('industry', [])
    sub = data.get('subdomain_focus', [])
    sug = data.get('suggestions', {})
    tld = data.get('tld_hint')

    nodes = []
    edges = []
    node_id = 0

    def add_node(label: str, group: str, title: str = '') -> int:
        nonlocal node_id
        nid = node_id
        nodes.append({'id': nid, 'label': label[:40], 'group': group, 'title': title or label})
        node_id += 1
        return nid

    def add_edge(fr: int, to: int):
        edges.append({'from': fr, 'to': to})

    root = add_node(d, 'root', f"Target: {d}\nIP: {data.get('ip', 'N/A')}")
    info_node = add_node('Domain Info', 'info')
    search_node = add_node('Search', 'search')
    pentest_node = add_node('Pentest', 'pentest')

    add_edge(root, info_node)
    add_edge(root, search_node)
    add_edge(root, pentest_node)

    for label, val in [
        ('Org', w.get('org')), ('Registrar', w.get('registrar')), ('Country', w.get('country')),
        ('Title', p.get('title')), ('Server', p.get('server')), ('Status', str(p.get('status')) if p.get('status') else None),
        ('Industry', ind[0][0] if ind else None), ('TLD', tld)
    ]:
        if val:
            n = add_node(f"{label}: {str(val)[:30]}", 'detail', str(val))
            add_edge(info_node, n)

    search_items = sug.get('search', []) or [
        f'site:{d} filetype:pdf', f'site:{d} inurl:admin', f'site:{d} inurl:api',
        f'site:{d} "api_key" OR "apikey" OR "secret"'
    ]
    for s in search_items[:8]:
        n = add_node(s[:35] + ('...' if len(s) > 35 else ''), 'item', s)
        add_edge(search_node, n)

    for pt in sug.get('pentest', [])[:12]:
        n = add_node(pt[:35] + ('...' if len(pt) > 35 else ''), 'item', pt)
        add_edge(pentest_node, n)

    if sub:
        for subname, focus in sub:
            sn = add_node(f"Sub: {subname}", 'subdomain', ', '.join(focus))
            add_edge(root, sn)
            for f in focus[:4]:
                fn = add_node(f, 'item', f)
                add_edge(sn, fn)

    return nodes, edges


def generate_html_report(all_data: List[Dict], output_path: str = 'target_intel_report.html') -> str:
    """Generate interactive HTML graph report."""
    import json
    from datetime import datetime

    nodes_list, edges_list = [], []
    for data in all_data:
        n, e = data_to_graph(data)
        offset = len(nodes_list)
        for node in n:
            node['id'] = node['id'] + offset
        for edge in e:
            edge['from'] += offset
            edge['to'] += offset
        nodes_list.extend(n)
        edges_list.extend(e)

    nodes_json = json.dumps([{'id': n['id'], 'label': n['label'], 'group': n['group'], 'title': n.get('title', '')} for n in nodes_list])
    edges_json = json.dumps(edges_list)

    groups = {
        'root': {'color': '#9b59b6', 'font': {'size': 18}},
        'info': {'color': '#3498db'},
        'search': {'color': '#2ecc71'},
        'pentest': {'color': '#e74c3c'},
        'subdomain': {'color': '#f39c12'},
        'detail': {'color': '#95a5a6'},
        'item': {'color': '#bdc3c7'},
    }

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SpyHunt Target Intel</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; }}
    .header {{ padding: 1.5rem 2rem; background: #161b22; border-bottom: 1px solid #30363d; }}
    .header h1 {{ font-size: 1.5rem; font-weight: 600; color: #58a6ff; }}
    .header p {{ font-size: 0.875rem; color: #8b949e; margin-top: 0.25rem; }}
    #graph {{ width: 100%; height: calc(100vh - 80px); }}
    .legend {{ position: fixed; bottom: 1rem; left: 1rem; background: #161b22; padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.75rem; border: 1px solid #30363d; }}
    .legend span {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
    .legend .root {{ background: #9b59b6; }}
    .legend .info {{ background: #3498db; }}
    .legend .search {{ background: #2ecc71; }}
    .legend .pentest {{ background: #e74c3c; }}
    .legend .sub {{ background: #f39c12; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>SpyHunt Target Intelligence</h1>
    <p>Interactive graph · {len(all_data)} target(s) · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
  </div>
  <div id="graph"></div>
  <div class="legend">
    <span class="root"></span> Target &nbsp;
    <span class="info"></span> Info &nbsp;
    <span class="search"></span> Search &nbsp;
    <span class="pentest"></span> Pentest &nbsp;
    <span class="sub"></span> Subdomain
  </div>
  <script>
    const nodes = new vis.DataSet({nodes_json});
    const edges = new vis.DataSet({edges_json});
    const container = document.getElementById('graph');
    const data = {{ nodes, edges }};
    const options = {{
      nodes: {{
        shape: 'dot',
        size: 16,
        font: {{ size: 12, color: '#c9d1d9' }},
        borderWidth: 2,
        borderWidthSelected: 3,
      }},
      edges: {{ width: 1.5, color: {{ color: '#30363d' }} }},
      physics: {{
        enabled: true,
        forceAtlas2Based: {{
          gravitationalConstant: -80,
          centralGravity: 0.01,
          springLength: 150,
          springConstant: 0.08,
        }},
        solver: 'forceAtlas2Based',
        stabilization: {{ iterations: 150 }},
      }},
      groups: {{
        root: {{ color: {{ background: '#9b59b6', border: '#7d3c98' }}, size: 25 }},
        info: {{ color: {{ background: '#3498db', border: '#2980b9' }} }},
        search: {{ color: {{ background: '#2ecc71', border: '#27ae60' }} }},
        pentest: {{ color: {{ background: '#e74c3c', border: '#c0392b' }} }},
        subdomain: {{ color: {{ background: '#f39c12', border: '#d68910' }} }},
        detail: {{ color: {{ background: '#95a5a6', border: '#7f8c8d' }}, size: 12 }},
        item: {{ color: {{ background: '#bdc3c7', border: '#95a5a6' }}, size: 12 }},
      }},
      interaction: {{ hover: true, tooltipDelay: 200 }},
    }};
    const network = new vis.Network(container, data, options);
  </script>
</body>
</html>'''

    with open(output_path, 'w') as f:
        f.write(html)
    return output_path


def run_target_intel(targets: List[str], html_output: Optional[str] = None) -> None:
    """Run target intel on URL or list of domains and print output."""
    from colorama import Fore, Style
    all_data = []
    valid_targets = [t.strip() for t in targets if t.strip() and not t.strip().startswith('#')]
    for i, t in enumerate(valid_targets):
        data = analyze_target(t)
        all_data.append(data)
        if len(valid_targets) > 1 and i > 0:
            print(f"\n\n  {Style.DIM}{'·' * 60}{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}[{i + 1}/{len(valid_targets)}]{Style.RESET_ALL}  {Fore.WHITE}{data.get('domain', t)}{Style.RESET_ALL}\n")
        print(format_output(data))

    if html_output and all_data:
        path = generate_html_report(all_data, html_output)
        print(f"\n  Report saved to {path}")
