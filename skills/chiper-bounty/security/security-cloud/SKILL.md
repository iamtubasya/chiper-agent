---
name: security-cloud
description: "Use during Phase 0C for cloud security audits."
metadata:
  hermes:
    budget_kb: 25
    tags: [cloud, aws, azure, gcp, kubernetes, security]
---

# Cloud Security Audit (Phase 0C-Cloud)

## ⛔ CANDIDATE RULE (MANDATORY — EVERY TEST)
- **Each test = one candidate. Finding something = mark candidate. CONTINUE to next test.**
- **Candidates become FINDINGS only after Phase 5 REPORT GATE (Phase 0F).**
- **DO NOT generate report during Phase 0C. Report = ABSOLUTE LAST.**
- **If you find CRITICAL → mark candidate → KEEP TESTING. Do NOT stop.**

## ⛔ Load Rules
- Load ONLY during Phase 0C for cloud/infra targets
- EVICT before loading Phase 0F (report)
- Budget: 25KB — read_file for detailed configs

---

## Cloud Audit Pipeline

### Step 1: Cloud Provider Identification
```bash
# DNS check for cloud providers
dig $DOMAIN CNAME | grep -iE 'amazonaws|cloudfront|azure|google|herokuapp|vercel|netlify'
# IP range check
whois $(dig +short $DOMAIN | head -1) | grep -iE 'amazon|azure|google'
```

### Step 2: IAM Enumeration (AWS)
```bash
# ScoutSuite (multi-cloud audit)
scout aws --access-keys $AK --secret-key $SK
# Cloudsplaining (IAM analysis)
cloudsplaining scan --access-key $AK --secret-key $SK
```
**Repos:** nccgroup/ScoutSuite (7.8K), salesforce/cloudsplaining (2.2K)

### Step 3: S3 Bucket Enumeration
```bash
# AWSBucketDump
python3 AWSBucketDump.py -t $TARGET -b $BUCKET_NAME
# Manual S3 enumeration
aws s3 ls s3://$BUCKET --recursive --summarize
# Look for: public read, public write, pre-signed URLs
```
**Repos:** jordanpotti/AWSBucketDump (1.5K)

### Step 4: Kubernetes Security
```bash
# kubestriker
kubestriker --kubeconfig $HOME/.kube/config
# validkube
validkube validate --kubeconfig $HOME/.kube/config
```
**Repos:** vchinnipilli/kubestriker (999), komodorio/validkube (836)

### Step 5: Container Security
```bash
# Docker security audit
docker scout cves $IMAGE
docker history $IMAGE
# Look for: running as root, secrets in env, exposed ports
```
**Repos:** madhuakula/hacker-container (295)

### Step 6: Azure Security
```bash
# ScoutSuite for Azure
scout azure --tenant-id $TENANT --subscription-id $SUB
# Azure-specific checks: KeyVault, Storage Accounts, App Service
```
**Repos:** Kyuu-Ji/Awesome-Azure-Pentest (1.2K)

---

## Cloud Vulnerability Checklist

### AWS
- [ ] S3 bucket public access (read/write)
- [ ] IAM privilege escalation paths
- [ ] Lambda function URL exposure
- [ ] EC2 metadata service (SSRF → credentials)
- [ ] RDS public access
- [ ] CloudTrail not enabled
- [ ] GuardDuty disabled
- [ ] Security groups too open (0.0.0.0/0)
- [ ] Secrets in SSM Parameter Store / Secrets Manager

### Azure
- [ ] Storage account public access
- [ ] KeyVault misconfiguration
- [ ] Azure AD privilege escalation
- [ ] App Service deployment credentials
- [ ] Cosmos DB public access

### GCP
- [ ] GCS bucket public access
- [ ] IAM policy misconfiguration
- [ ] Cloud Functions URL exposure
- [ ] GKE cluster security

### Kubernetes
- [ ] RBAC misconfiguration
- [ ] Pod security policies
- [ ] Secrets in etcd
- [ ] Dashboard exposure
- [ ] Service mesh security

---

## CloudGoat (Practice Labs)
```bash
# CloudGoat: vulnerable-by-design AWS deployment
git clone https://github.com/RhinoSecurityLabs/cloudgoat
cd cloudgoat
python3 cloudgoat.py lambda_privesc us-east-1
```
**Repos:** RhinoSecurityLabs/cloudgoat (3.7K)

---

## Integrated Repos (14)

| Repo | Stars | What We Took |
|------|-------|--------------|
| nccgroup/ScoutSuite | 7.8K | Multi-cloud audit framework |
| jassics/security-study-plan | 5.1K | Study plan (pentest/cloud roles) |
| RhinoSecurityLabs/cloudgoat | 3.7K | AWS vuln lab patterns |
| salesforce/cloudsplaining | 2.2K | AWS IAM audit tool |
| nccgroup/Scout2 | 1.7K | AWS audit (legacy) |
| jordanpotti/AWSBucketDump | 1.5K | S3 bucket enumeration |
| Kyuu-Ji/Awesome-Azure-Pentest | 1.2K | Azure pentest resources |
| SecurityFTW/cs-suite | 1.2K | Cloud posture audit |
| vchinnipilli/kubestriker | 999 | K8s security audit |
| ASCIT31/Dark-Moon | 946 | AI multi-domain pentest |
| DockerSecurityPlayground/DSP | 631 | Network security study |
| madhuakula/hacker-container | 295 | Cloud native security container |
| arch3rPro/Pentest-Docker | 115 | Pentest container platform |
| toniblyx/my-arsenal-of-aws-security-tools | 9.5K | AWS security tool index |

---

## Cross-References
- Recon → `security-recon` (Phase 0B)
- Scanners → `security-scanners` (Phase 0C)
- Attack playbooks → `security-web-attacks` (Phase 0C)
- Report → `bug-report-delivery` (Phase 0F, ABSOLUTE LAST)
