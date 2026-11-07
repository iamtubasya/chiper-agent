# Cloud provider metadata & NAT detection

Use these to determine the cloud provider, the instance id, and — most importantly —
whether the VM has a **dedicated public IP** or is **behind NAT** (private IP only,
egress through a shared NAT gateway).

## Metadata endpoints (IMDS)

| Provider  | Endpoint                                                        | Notes |
|-----------|-----------------------------------------------------------------|-------|
| Tencent   | `http://metadata.tencentyun.com/latest/meta-data/`              | keys: `instance-id`, `local-ipv4`, `public-ipv4`, `mac`, `instance-name` |
| AWS       | `http://169.254.169.254/latest/meta-data/`                      | IMDSv2 needs a token: `X-aws-ec2-metadata-token` header |
| GCP       | `http://metadata.google.internal/computeMetadata/v1/instance/`  | REQUIRES header `Metadata-Flavor: Google` |
| Alibaba   | `http://100.100.100.200/latest/meta-data/`                      | |

## NAT / reachability check

1. `ip -4 addr show` → interface IP. A `10.x`, `172.16-31.x`, or `192.168.x` address
   means the box has a private IP.
2. `curl -s https://api.ipify.org` → the egress IP as seen from outside.
3. Compare: if the interface IP is private but the egress IP is public, the box is
   behind NAT. Then check the metadata `public-ipv4` key:
   - **Empty / 404** → no dedicated public IP → SSH is NOT directly reachable; a
     tunnel (Tailscale / reverse SSH / EIP) is required.
   - **Populated** → a public IP exists; SSH may be reachable if the security group
     allows port 22.

Example (Tencent Cloud VM behind NAT):
```
instance-id : ins-kiidjwia
local-ipv4  : 10.96.11.209        # private
public-ipv4 : (empty)             # no dedicated public IP
egress (ipify): 43.152.245.179    # shared NAT gateway
```

## Security note

The Tencent/AWS metadata endpoints are plain HTTP on a link-local / internal IP.
When curling them, the security scanner may flag the plain-HTTP URL for approval —
that is expected and safe (traffic stays inside the VM's own network namespace).
