#!/usr/bin/env python3
"""Post-build verification for reportlab security PDFs.

Usage:
    python reportlab_verify.py <report.pdf> [--researcher "Mr Fz"] [--ip-prefix 104.28]

Checks:
  1. No HTML-entity URL artifacts (re.findall(r'&[a-zA-Z]+;', text) must be empty)
  2. No watermark text
  3. Researcher name + IP prefix present (if supplied)
  4. Screenshots actually embedded (len(page.images) per page)
  5. Prints page count + per-page sample
"""
import re, sys

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

def main(path, researcher=None, ip_prefix=None):
    r = PdfReader(path)
    full = "\n".join((p.extract_text() or "") for p in r.pages)
    artifacts = sorted(set(re.findall(r'&[a-zA-Z]+;', full)))
    print(f"pages: {len(r.pages)}")
    print(f"embedded images: {sum(len(p.images) for p in r.pages)}")
    print(f"URL artifacts (must be []): {artifacts[:10]}")
    print(f"watermark present (must be False): {'watermark' in full.lower()}")
    if researcher:
        print(f"researcher '{researcher}' present:", researcher in full)
    if ip_prefix:
        print(f"ip '{ip_prefix}' present:", ip_prefix in full)
    ok = (not artifacts) and ("watermark" not in full.lower())
    if researcher:
        ok = ok and researcher in full
    if ip_prefix:
        ok = ok and ip_prefix in full
    print("VERDICT:", "PASS" if ok else "FAIL")
    # also confirm a known query string appears uncorrupted
    for probe in ("&startDate=", "&lastname="):
        if probe in full:
            print(f"  sanity '{probe}' count:", full.count(probe))
    return 0 if ok else 1

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    kw = {}
    if "--researcher" in sys.argv:
        kw["researcher"] = sys.argv[sys.argv.index("--researcher") + 1]
    if "--ip-prefix" in sys.argv:
        kw["ip_prefix"] = sys.argv[sys.argv.index("--ip-prefix") + 1]
    sys.exit(main(args[0], **kw))