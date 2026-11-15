# Port Scanning

> tags: recon, beginner, intermediate

> related: Recon/Subdomain-Enumeration, Recon/Content-Discovery, Recon/API-Discovery

Port Scanning
Everyone defaults to the top 1000 ports and calls it done. You'll miss a lot that way. The Jenkins instance running on 8080, the Kubernetes dashboard on 10250, the Elasticsearch cluster on 9200  -  all of these pay out regularly and all of them are off the default nmap port range.

The Strategy: Masscan First, Nmap Second
Masscan is fast  -  10M packets/second fast. It doesn't do service detection worth anything, but it can scan all 65535 ports on a /24 in minutes. Nmap is accurate, fingerprints services properly, and runs scripts  -  but it's slow at scale. Use them together.

Step 1: Masscan  -  All Ports, Fast
# Scan a single host, all ports
masscan -p1-65535 1.2.3.4 --rate=10000 -oG masscan_output.txt
 
# Scan a range from a file
masscan -p1-65535 -iL ip_list.txt --rate=10000 \
  --exclude 255.255.255.255 \
  -oG masscan_results.gnmap
 
# Parse the open ports out
grep "Ports:" masscan_results.gnmap | \
  awk '{print $2, $5}' | \
  sed 's|/open.*||' > open_ports.txt
Rate tuning  -  don't smash it at max on a program unless the scope explicitly allows aggressive scanning. 5000-10000 is a safe middle ground.

Step 2: Nmap  -  Service Fingerprinting on Open Ports
Take the ports masscan found and throw them at nmap for proper identification.
# Parse masscan output and build nmap input
grep open masscan_results.gnmap | awk '{print $2}' | sort -u > live_hosts.txt
grep open masscan_results.gnmap | grep -oP '\d+/open' | \
  grep -oP '^\d+' | sort -un | tr '\n' ',' | sed 's/,$//' > open_ports_list.txt
 
# Run nmap only on discovered open ports
nmap -sV -sC -p $(cat open_ports_list.txt) \
  -iL live_hosts.txt \
  --open -T4 \
  -oA nmap_services
 
# Or per-host (cleaner output, slower)
while IFS=: read host ports; do
  nmap -sV -sC -p $ports --open -T4 $host -oN "nmap_$host.txt"
done < host_ports_mapping.txt

A Full Workflow Script
#!/bin/bash
TARGET_FILE="$1"  # file with IPs/CIDRs
 
# Phase 1: masscan
masscan -p1-65535 -iL $TARGET_FILE \
  --rate=5000 \
  --exclude 255.255.255.255 \
  -oG masscan_all.gnmap
 
# Phase 2: extract host:port pairs
python3 - << 'EOF'
import re
 
hosts = {}
with open("masscan_all.gnmap") as f:
    for line in f:
        m = re.search(r'Host: (\S+).*Ports: ([\d,/a-z ]+)', line)
        if m:
            host = m.group(1)
            ports = re.findall(r'(\d+)/open', m.group(2))
            if host not in hosts:
                hosts[host] = set()
            hosts[host].update(ports)
 
with open("host_ports.txt", "w") as f:
    for host, ports in hosts.items():
        f.write(f"{host}:{','.join(sorted(ports, key=int))}\n")
EOF
 
# Phase 3: nmap on each host's open ports
while IFS=: read host ports; do
  nmap -sV --version-intensity 5 -sC -p $ports \
    --open -T4 -Pn $host \
    -oN "nmap_${host//\./_}.txt" 2>/dev/null
done < host_ports.txt

Non-Standard Ports That Pay Out
These are the ports worth paying attention to when they show up open.











































































PortServiceWhy It Matters8080, 8443, 8888Alt HTTP/HTTPSAdmin panels, dev servers, proxies9200, 9300ElasticsearchUnauthenticated data access27017MongoDBUnauthenticated access common6379RedisOften open with no auth5601KibanaFull log access2375, 2376Docker APIRCE via exposed daemon10250Kubernetes API (kubelet)Node-level RCE4848GlassFish adminWeak default creds8161ActiveMQDefault admin/admin9090Prometheus/CockpitMetrics exposure, auth bypass3000Grafana, dev appsDefault creds, old vulns5000Flask dev server, Docker registryDev exposure11211MemcachedUnauthenticated cache dump
# Quick check  -  anything interesting on common non-standard ports?
nmap -p 8080,8443,9200,27017,6379,5601,2375,10250,3000,5000 \
  -sV --open -iL live_hosts.txt -oG interesting_ports.gnmap

HTTP Service Discovery from Scan Results
Once you have services fingerprinted, pipe everything that's HTTP/HTTPS into httpx.
# Extract anything that looks like a web service
grep -E "(http|https|nginx|apache|iis)" nmap_services.gnmap | \
  awk '{print $2}' > potential_web.txt
 
# Or use nmap's XML output more cleanly
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('nmap_services.xml')
for host in tree.findall('.//host'):
    addr = host.find('.//address').get('addr')
    for port in host.findall('.//port'):
        if port.find('state').get('state') == 'open':
            portid = port.get('portid')
            service = port.find('service')
            if service is not None and 'http' in service.get('name',''):
                print(f'{addr}:{portid}')
" > http_services.txt
 
httpx -l http_services.txt -silent -title -status-code -tech-detect

Scan Flow
graph LR
    A[IP List] --> B[masscan  -  65k ports]
    B --> C[Extract open ports per host]
    C --> D[nmap  -  service detection on open ports]
    D --> E{What's running?}
    E --> F[HTTP services → httpx → content discovery]
    E --> G[Databases → check auth]
    E --> H[Admin panels → default creds]
    E --> I[APIs → enumerate]


Related

Subdomain Enumeration  -  get your host list here first
Content Discovery  -  what to do once you have open HTTP services
API Discovery  -  APIs show up on non-standard ports constantly
