# IAM Privilege Escalation

> tags: cloud, aws, advanced, critical

> related: Attack-Surface/Cloud/AWS/, Attack-Surface/Cloud/AWS/S3-Misconfiguration, Attack-Surface/Cloud/AWS/Lambda

AWS IAM Privilege Escalation
IAM privesc is where cloud bugs go from interesting to critical. You start with a low-privilege key - maybe leaked in a JS file or grabbed via SSRF - and work up to admin. The key insight: IAM is complex enough that over-permissive policies are the norm, not the exception. Rhino Security has the canonical list of privesc paths; Pacu automates most of them.
Step 1: Enumerate What You Have
Never assume you know what a key can do from its name or the role it's attached to.
# Install enumerate-iam
pip install enumerate-iam
 
# Run it against your creds (this makes a lot of API calls - noisy)
python enumerate-iam.py --access-key AKIA... --secret-key ... --session-token ...
 
# Quieter manual approach: check specific high-value permissions
aws iam get-user
aws iam list-attached-user-policies --user-name USERNAME
aws iam list-user-policies --user-name USERNAME
aws iam get-user-policy --user-name USERNAME --policy-name POLICYNAME
 
# For roles
aws iam get-role --role-name ROLENAME
aws iam list-attached-role-policies --role-name ROLENAME
aws sts get-caller-identity
Step 2: Known Escalation Paths
These are the most common paths I hit. Full list at Rhino Security's research.





















































PermissionEscalation Methodiam:CreatePolicyVersionCreate new policy version with *:* and set as defaultiam:SetDefaultPolicyVersionRevert to an older, more permissive versioniam:PassRole + ec2:RunInstancesLaunch instance with admin role, exfil creds from metadataiam:PassRole + lambda:CreateFunction + lambda:InvokeFunctionCreate Lambda with admin role, invoke to run codeiam:PassRole + glue:CreateDevEndpointClassic Rhino path, less common nowiam:CreateAccessKeyCreate new key for another useriam:CreateLoginProfileAdd console password to IAM user that doesn't have oneiam:UpdateLoginProfileChange another user's console passwordiam:AttachUserPolicyAttach AdministratorAccess to yourselfiam:PutUserPolicyInline policy with full permissionssts:AssumeRoleAssume a more privileged role if trust policy allows
Step 3: Pacu for Automation
Pacu is the go-to. Use iam__privesc_scan to automatically identify and optionally exploit escalation paths.
# Install
git clone github.com/RhinoSecurityLabs/pacu
cd pacu && pip install -r requirements.txt
 
# Start Pacu
python3 pacu.py
 
# Inside Pacu
set_keys  # enter your creds
whoami    # confirm identity
run iam__enum_permissions  # enumerate what you can do
run iam__privesc_scan       # identify privesc paths
Pacu will list available paths and ask if you want to attempt them. In a bug bounty context, I usually stop at identification and document the path rather than fully exploiting to admin unless the program explicitly allows it.
Role Chaining
Role chaining is underrated. If role A can assume role B, and role B can assume role C, you may end up with permissions that no single role was supposed to have, especially if session tag constraints aren't enforced.
# Assume a role
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME \
  --role-session-name pentest
 
# Use the returned credentials to assume the next role
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
aws sts assume-role --role-arn arn:aws:iam::ACCOUNT_ID:role/NEXT_ROLE ...
Look for trust policies with "Principal": {"AWS": "*"} or overly broad conditions.
Cross-Account Escalation
If the role's trust policy allows principals from other accounts:
aws iam get-role --role-name ROLENAME | jq '.Role.AssumeRolePolicyDocument'
Check if the principal is * or references accounts you control. Some programs have dev accounts that can assume prod roles.
Reporting Privesc
For bug bounty reports, I always:

Document the starting permissions precisely (paste the policy)
Show the exact escalation path step by step
Demonstrate impact with aws sts get-caller-identity showing the elevated identity
Stop before doing anything destructive or accessing prod data beyond what proves the bug

Related

AWS Overview
S3 Misconfiguration - often where initial creds come from
Lambda - iam:PassRole + Lambda is a top escalation path
