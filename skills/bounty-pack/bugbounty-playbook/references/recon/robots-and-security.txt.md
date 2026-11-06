# robots.txt, security.txt & sitemap.xml

> tags: recon, beginner

> related: Recon/Content-Discovery, Recon/API-Documentation-Discovery, Recon/Wayback-Mining

robots.txt, security.txt & sitemap.xml
These three files take five seconds to check and consistently surface admin paths, staging environments, and programme contact details that aren't in the scope document. They're the first thing to pull on any new target.

robots.txt
The Disallow: entries in robots.txt were written by someone who didn't want search engines indexing those paths. That same list is a map of paths worth testing.
curl -s target.com/robots.txt
 
# Common interesting patterns in output:
# Disallow: /admin/
# Disallow: /internal/
# Disallow: /staging/
# Disallow: /api/private/
# Disallow: /wp-admin/
# Disallow: /_debug/
 
# Extract all disallowed paths
curl -s target.com/robots.txt | \
  grep -i "Disallow:" | \
  awk '{print $2}' | sort -u
Not every disallowed path is accessible. Many return 403. But some return 200, 301, or 401  -  which means the resource exists and access controls are worth probing.

security.txt
RFC 9116 standardises a machine-readable file at /.well-known/security.txt (and the legacy path /security.txt) that organisations use to publish their vulnerability disclosure details.
curl -s target.com/.well-known/security.txt
curl -s target.com/security.txt
 
# Standard fields you'll see:
# Contact: bugcrowd.com/target     <-- the actual programme
# Contact: mailto:security@target.com
# Expires: 2026-01-01T00:00:00.000Z
# Acknowledgments: target.com/hall-of-fame   <-- past reports
# Scope: target.com/bugbounty/scope
# Policy: target.com/responsible-disclosure
The Acknowledgments URL often lists previously rewarded researchers and sometimes the type of bug. The Scope or Policy URL may be more detailed than what's in the bounty platform brief. Both are worth reading before you start testing.

sitemap.xml
sitemap.xml is intended for search engine crawlers and lists every URL the site considers canonical. It's noisier than robots.txt but more thorough.
curl -s target.com/sitemap.xml | \
  grep -oE "<loc>[^<]+" | sed 's/<loc>//'
 
# Some sites have a sitemap index pointing at multiple sitemaps
curl -s target.com/sitemap_index.xml | \
  grep -oE "<loc>[^<]+" | sed 's/<loc>//'
 
# Interesting URLs to look for in sitemap output:
# /api/ paths
# /admin/ paths (misconfigured  -  shouldn't be in public sitemap)
# Non-www subdomains referenced as canonical
# Paths with ID parameters  -  good IDOR candidates

Related

Content Discovery  -  paths from robots.txt seed your wordlist runs
API Documentation Discovery  -  security.txt sometimes links directly to scope docs
Wayback Mining  -  older versions of robots.txt reveal paths removed from current site
