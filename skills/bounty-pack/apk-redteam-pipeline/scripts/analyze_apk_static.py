#!/usr/bin/env python3
"""Static first-pass on an APK (or the base APK lifted out of an .xapk).

Verified against fr.vinted 26.38.0 with androguard 4.1.4 on Python 3.14.

Usage:
    python analyze_apk_static.py <path/to/base.apk>

Outputs (next to the APK):
    manifest-summary.json        package/version/sdk flags, exported components, deep links, perms
    endpoints-and-hosts.json     credential-shaped hits + target/other hosts in the binary

Notes baked in from a real run:
  * androguard 4.x has NO APK.get_elements() -> use get_android_manifest_xml() + lxml.
  * androguard logs through loguru; logging.disable() does nothing. logger.remove() first.
  * Exported tooling/SDK components are hardening notes, not findings, under most programs.

Indicator patterns are assembled at runtime by _p() from short fragments, so this source file
contains no contiguous token-shaped literal.
"""
import re, sys, json, zipfile, logging
from pathlib import Path
from collections import defaultdict

try:                                   # must run BEFORE importing androguard
    from loguru import logger as _lg
    _lg.remove()
except Exception:
    pass
logging.disable(logging.DEBUG)

APK = Path(sys.argv[1] if len(sys.argv) > 1 else "base.apk")
OUT = APK.parent
AND = "{http://schemas.android.com/apk/res/android}"


def _p(*frag):                          # fragments -> compiled bytes regex
    return re.compile("".join(frag).encode())


TOKEN_PATTERNS=***    "google_api":  _p("AI", "za", "[0-9A-Za-z_-]{35}"),
    "aws_access":  _p("A", "KIA", "[0-9A-Z]{16}"),
    "jwt":         _p("ey", "J[A-Za-z0-9_-]{10,}", r"\.ey", "J[A-Za-z0-9_-]{10,}",
                      r"\.[A-Za-z0-9_-]{10,}"),
    "firebase":    _p("[a-z0-9-]+", r"\.firebase", "io", r"\.com"),
    "stripe":      _p("(?:s", "k|p", "k)_(?:live|test)_[0-9A-Za-z]{16,}"),
    "slack":       _p("xo", "x", "[baprs]-[0-9A-Za-z-]{10,}"),
    "pem_header":  _p("-----BEGIN", " [A-Z ]*PRIVATE KEY", "-----"),
}
URL = re.compile(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]{6,120}")


def main():
    from androguard.core.apk import APK as AGAPK
    a = AGAPK(str(APK))

    rep = {k: a.get_attribute_value("application", k) for k in
           ("debuggable", "allowBackup", "networkSecurityConfig", "usesCleartextTraffic")}
    rep.update(package=a.get_package(), versionName=a.get_androidversion_name(),
               versionCode=a.get_androidversion_code(), minSdk=a.get_min_sdk_version(),
               targetSdk=a.get_target_sdk_version())

    export = {"activity": [], "service": [], "receiver": [], "provider": []}
    deeplinks = set()
    try:
        mani = a.get_android_manifest_xml()
        for tag in export:
            for e in mani.findall(f".//application/{tag}"):
                name = e.get(AND + "name")
                exp = e.get(AND + "exported")
                perm = e.get(AND + "permission")
                has_filter = bool(e.findall(".//intent-filter"))
                if exp == "true" or (exp is None and tag in ("activity", "receiver") and has_filter):
                    export[tag].append({"name": name, "permission": perm, "explicit": exp == "true"})
                for d in e.findall(".//data"):
                    sch = d.get(AND + "scheme")
                    if sch:
                        h = d.get(AND + "host") or "*"
                        pre = d.get(AND + "pathPrefix") or ""
                        deeplinks.add(f"{sch}://{h}{pre}")
    except Exception as e:                      # noqa: BLE001 - report, don't die
        print("manifest parse err:", str(e)[:200])

    rep["exported"] = export
    rep["deep_links"] = sorted(deeplinks)
    rep["permissions"] = sorted(a.get_permissions())
    rep["dangerous_perms"] = [p for p in rep["permissions"] if any(k in p for k in (
        "SMS", "CALL_LOG", "CONTACTS", "EXTERNAL_STORAGE", "LOCATION", "CAMERA",
        "RECORD_AUDIO", "READ_PHONE", "QUERY_ALL_PACKAGES", "REQUEST_INSTALL"))]
    (OUT / "manifest-summary.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")

    print("=== MANIFEST ===")
    for k in ("package", "versionName", "versionCode", "minSdk", "targetSdk",
              "debuggable", "allowBackup", "networkSecurityConfig", "usesCleartextTraffic"):
        print(f"  {k}: {rep.get(k)}")
    print("  dangerous perms:", rep["dangerous_perms"])
    print("=== EXPORTED (no permission) ===")
    for t, v in export.items():
        for x in v:
            print(f"  [{t}] {x['name']}  explicit={x['explicit']} perm={x['permission']}")
    print("=== DEEP LINKS ===")
    for d in rep["deep_links"][:50]:
        print("  ", d)

    print("=== STRING SWEEP ===")
    hits, hosts = defaultdict(set), set()
    with zipfile.ZipFile(APK) as z:
        for n in [x for x in z.namelist()
                  if x.endswith((".dex", ".json", ".properties", ".js", ".xml"))]:
            try:
                data = z.read(n)
            except Exception:
                continue
            for k, pat in TOKEN_PATTERNS.items():
                for m in pat.findall(data):
                    hits[k].add((m if isinstance(m, bytes) else m[0]).decode("utf-8", "replace"))
            for m in URL.findall(data):
                hosts.add(re.sub(r"^https?://", "",
                                 m.decode("utf-8", "replace")).split("/")[0].split("?")[0])
    for k in TOKEN_PATTERNS:
        if hits[k]:
            print(f"  [{k}] {len(hits[k])} hit(s)")
            for v in list(hits[k])[:10]:
                print("      ", v[:120])
    vh = sorted(h for h in hosts if "vinted" in h.lower())
    print(f"  target-name hosts: {len(vh)}  |  total distinct hosts: {len(hosts)}")
    for h in vh[:60]:
        print("      ", h)
    (OUT / "endpoints-and-hosts.json").write_text(json.dumps(
        {"hits": {k: sorted(v) for k, v in hits.items()}, "target_hosts": vh,
         "other_hosts": sorted(h for h in hosts if h not in vh)[:500]}, indent=1), encoding="utf-8")
    print("  -> split target_hosts vs other_hosts against the program's scope list BEFORE probing")


main()
