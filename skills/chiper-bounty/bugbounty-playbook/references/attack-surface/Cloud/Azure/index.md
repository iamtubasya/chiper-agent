# Azure Attack Surface

> tags: cloud, azure

> related: Attack-Surface/Cloud/, Attack-Surface/Cloud/AWS/, Attack-Surface/CI-CD/

Azure Attack Surface
Azure shows up less than AWS in bug bounty programs but the orgs that run it tend to be large enterprises - banks, healthcare, Fortune 500. That means higher payouts and more interesting targets. The three areas I focus on: Blob storage (same class of misconfig as S3), Entra ID (formerly Azure Active Directory), and Function Apps.
Core Services to Target

































ServiceWhat I'm Looking ForBlob StoragePublic containers, SAS token abuse, anonymous accessEntra ID (AAD)App registrations, service principals, consent phishingFunction AppsExposed function keys, managed identity abuseKey VaultOver-permissive access policies, secrets accessible via managed identityContainer RegistryPublic registries, over-shared access tokensApp ServiceEnvironment variables, managed identity misconfiguration
SSRF to Azure Metadata
# Requires Metadata: true header
curl -H "Metadata: true" \
  "http://169.254.169.254/metadata/instance?api-version=2021-02-01"
 
# Get managed identity token via SSRF
curl -H "Metadata: true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=management.azure.com/"
The token you get is a JWT for the managed identity. Use it with the Azure REST API or az CLI.
Blob Storage
Azure Blob Storage containers can have three access levels: Private, Blob (anonymous read for blobs), Container (anonymous read + list). Finding public containers:
# If you know the storage account name
curl https://ACCOUNT.blob.core.windows.net/CONTAINER
 
# Enumerate common container names
for container in assets uploads public images backups logs data; do
  curl -s -o /dev/null -w "%{http_code} $container\n" \
    "https://ACCOUNT.blob.core.windows.net/$container?restype=container&comp=list"
done
Storage account names are globally unique and show up in JS source, network traffic, and public repos.
SAS Token Abuse
Shared Access Signature tokens are like presigned URLs for Azure. They're time-limited but often generated with excessive permissions or long expiry:
# A SAS token in a URL looks like:
# account.blob.core.windows.net/container/file
 
# Decode the token to check permissions (sp= field)
# r = read, w = write, d = delete, l = list, a = add, c = create, u = update
Check mobile apps, JS bundles, and API responses for embedded SAS tokens. A sp=rwdl token with a 2025+ expiry is a solid finding.
Entra ID (Azure AD)
# Authenticate with az CLI
az login
 
# List app registrations (if you have reader access)
az ad app list --all --query '[].{name:displayName, appId:appId}'
 
# Check for overly permissive app permissions
az ad app permission list --id APP_ID
 
# Service principal enumeration
az ad sp list --all --query '[].{name:displayName, appId:appId}'
Look for app registrations with:

oauth2AllowImplicitFlow: true (legacy implicit flow, token in URL fragment)
Broad Microsoft Graph permissions (User.ReadWrite.All, Directory.ReadWrite.All)
Missing replyUrls restrictions (open redirect in OAuth)
Multi-tenant apps that accept tokens from any tenant

Managed Identity Abuse
If you have SSRF on an Azure VM or App Service, the managed identity gives you an Azure AD token. What you can do with it depends on the roles assigned to that managed identity.
# With a managed identity token for management.azure.com
az login --identity
 
# What subscriptions can we see?
az account list
 
# What resources in this subscription?
az resource list
Function App Keys
Azure Functions are secured by function keys (a secret query parameter or header). These leak in the same places Lambda env vars do: repos, config files, CI/CD logs.
# If you have the function key
curl "https://FUNCAPP.azurewebsites.net/api/FUNCTION_NAME
 
# Check host keys (broader than function keys)
curl -H "x-functions-key: HOST_KEY" \
  "https://FUNCAPP.azurewebsites.net/api/FUNCTION_NAME"
Related

Cloud Overview
AWS - for comparison on metadata service exploitation
CD - Azure DevOps pipelines leak secrets too
