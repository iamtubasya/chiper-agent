#!/usr/bin/env python3
"""First-pass static analysis of an APK (or the base APK extracted from an .xapk).

Answers the questions that decide whether a mobile target is worth deeper work:
  - is it a debug build / cleartext-permitting build?
  - are there exported components (activities/services/receivers/providers) with no permission?
  - what deep links / custom schemes does it claim?
  - any hardcoded credential, and which hosts does it talk to?

Usage:
    pip install androguard
    python analyze_apk.py <base.apk> [out_dir]

Writes manifest-summary.json + endpoints-and-secrets.json next to the APK.
No jadx needed. Verified against a 129 MB base APK from a 141 MB .xapk bundle.

NOTE: androguard 4.x has no APK.get_elements(); use get_android_manifest_xml().
NOTE: androguard logs via loguru — logger.remove() is required, logging.disable() is not enough.
"""
import logging
import re
import sys
import json
import zipfile
from pathlib import Path
from collections import defaultdict

try:                                    # androguard uses loguru, not stdlib logging
    from loguru import logger as _lg
    _lg.remove()
except Exception:
    pass
logging.disable(logging.DEBUG)

APK = Path(sys.argv[1] if len(sys.argv) > 1 else "base.apk")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else APK.parent
OUT.mkdir(parents=True, exist_ok=True)
A = "{http://schemas.android.com/apk/res/android}"

# Post-Android-12 a component is exported only if android:exported is stated, BUT many apps still
# rely on the legacy rule (an intent-filter implies exported). Flag both, mark which is explicit.
LEGACY_IMPLIES_EXPORTED = ("activity", "receiver")


def main():
    from androguard.core.apk import APK as AGAPK
    a = AGAPK(str(APK))

    rep = {
        "package": a.get_package(),
        "versionName": a.get_androidversion_name(),
        "versionCode": a.get_androidversion_code(),
        "minSdk": a.get_min_sdk_version(),
        "targetSdk": a.get_target_sdk_version(),
        "debuggable": a.get_attribute_value("application", "debuggable"),
        "allowBackup": a.get_attribute_value("application", "allowBackup"),
        "networkSecurityConfig": a.get_attribute_value("application", "networkSecurityConfig"),
        "usesCleartextTraffic": a.get_attribute_value("application", "usesCleartextTraffic"),
    }

    exported = {"activity": [], "service": [], "receiver": [], "provider": []}
    deeplinks = set()
    try:
        mani = a.get_android_manifest_xml()          # lxml element (4.x API)
        for tag in exported:
            for e in mani.findall(f".//application/{tag}"):
                name = e.get(A + "name")
                exp = e.get(A + "exported")          # string "true"/"false"/None
                perm = e.get(A + "permission")
                has_filter = bool(e.findall(".//intent-filter"))
                if exp == "true" or (exp is None and tag in LEGACY_IMPLIES_EXPORTED and has_filter):
                    exported[tag].append({"name": name, "permission": perm,
                                          "explicit": exp == "true"})
                for d in e.findall(".//data"):
                    sch = d.get(A + "scheme")
                    if sch:
                        deeplinks.add(f"{sch}://{d.get(A + 'host') or '*'}"
                                      f"{d.get(A + 'pathPrefix') or ''}")
    except Exception as e:
        print("manifest parse err:", str(e)[:200])

    rep["exported"] = exported
    rep["deep_links"] = sorted(deeplinks)
    rep["permissions"] = sorted(a.get_permissions())
    rep["dangerous_perms"] = [p for p in rep["permissions"] if any(k in p for k in (
        "SMS", "CALL_LOG", "CONTACTS", "EXTERNAL_STORAGE", "LOCATION", "CAMERA",
        "RECORD_AUDIO", "READ_PHONE", "QUERY_ALL_PACKAGES", "REQUEST_INSTALL"))]
    (OUT / "manifest-summary.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")

    print("=== MANIFEST ===")
    for k in ("package", "versionName", "versionCode", "minSdk", "targetSdk", "debuggable",
              "allowBackup", "networkSecurityConfig", "usesCleartextTraffic"):
        print(f"  {k}: {rep.get(k)}")
    print("  dangerous perms:", rep["dangerous_perms"])
    print("=== EXPORTED COMPONENTS ===")
    for tag, rows in exported.items():
        for r in rows:
            print(f"  [{tag}] {r['name']}  explicit={r['explicit']} perm={r['permission']}")
    print("=== DEEP LINKS ===")
    for d in rep["deep_links"][:60]:
        print("  ", d)

    print("=== STRING SWEEP (raw dex/resource scan) ===")
    pats = {
        "google_key": re.compile(rb"AIza[0-9A-Za-z_\-]{35}"),
        "aws_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
        "jwt": re.compile(rb"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
        "firebase": re.compile(rb"[a-z0-9-]+\.firebaseio\.com|[a-z0-9-]+\.firebaseapp\.com"),
        "stripe": re.compile(rb"(?:sk|pk)_(?:live|test)_[0-9A-Za-z]{16,}"),
        "slack": re.compile(rb"xox[baprs]-[0-9A-Za-z-]{10,}"),
        "url": re.compile(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]{6,120}"),
    }
    hits = defaultdict(set)
    hosts = set()
    with zipfile.ZipFile(APK) as z:
        for n in [x for x in z.namelist()
                  if x.endswith((".dex", ".json", ".properties", ".js", ".xml"))]:
            try:
                data = z.read(n)
            except Exception:
                continue
            for kind, pat in pats.items():
                for raw in pat.findall(data):
                    s = raw.decode("utf-8", "replace")
                    if kind == "url":
                        hosts.add(re.sub(r"^https?://", "", s).split("/")[0].split("?")[0])
                    else:
                        hits[kind].add(s)

    for kind in ("google_key", "aws_key", "jwt", "firebase", "stripe", "slack"):
        if hits[kind]:
            print(f"  [{kind}] {len(hits[kind])} hit(s)")
            for v in list(hits[kind])[:10]:
                print("      ", v[:120])
    print(f"  total distinct hosts: {len(hosts)}")
    (OUT / "endpoints-and-secrets.json").write_text(json.dumps(
        {"secrets": {k: sorted(v) for k, v in hits.items()},
         "hosts": sorted(hosts)}, indent=1), encoding="utf-8")

    print("\nNEXT: split hosts into in-scope vs out-of-scope against the program's target list "
          "BEFORE touching any of them. Hosts embedded in a client build are a discovery "
          "opportunity, not an authorisation.")


main()
