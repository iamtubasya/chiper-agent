# Chaos Project

> tags: programs

> related: Programs/Platforms/HackerOne, Programs/Platforms/Bugcrowd, Programs/Platforms/Intigriti, Programs/Selection/Competition-Assessment, Programs/Selection/New-Programs

Chaos Project
Chaos is not a bug bounty platform. It's a dataset. ProjectDiscovery maintains a curated, continuously updated list of in-scope targets aggregated from public bug bounty programmes across HackerOne, Bugcrowd, Intigriti, and others. If your recon pipeline still relies on manually pulling scope from program pages, Chaos is worth understanding.

What Chaos Is
ProjectDiscovery publishes a structured feed of bug bounty scope data at chaos.projectdiscovery.io and via GitHub at github.com/projectdiscovery/public-bugbounty-programs. The dataset includes:

Domains and subdomains listed as in-scope across public programmes
The source programme and platform for each entry
Regular updates as programmes add or change scope

The data is free to access and use. ProjectDiscovery provides it specifically to support security research and recon tooling.

What It's Not
Chaos does not:

Run programmes itself
Accept vulnerability reports
Pay bounties
Verify that scope entries are still active or current

It's a data feed. The accuracy depends on how recently the data was synced from source programmes, and some entries will be stale. Treat it as a starting point, not ground truth. Always verify that a target is still in scope on the actual programme page before testing.

The CLI and API
ProjectDiscovery provides a CLI tool called chaos-client for pulling the dataset programmatically:
# Install
go install github.com/projectdiscovery/chaos-client/cmd/chaos@latest
 
# List all programme domains
chaos -d target.com -o output.txt
 
# Pull a specific programme's scope
chaos -key <API_KEY> -d target.com
An API key is required for most operations beyond basic queries. Keys are free via the ProjectDiscovery dashboard at cloud.projectdiscovery.io.

Integrating with Your Recon Pipeline
The primary use case is feeding Chaos output into subdomain enumeration and asset discovery tooling. A standard integration pattern:
# Pull in-scope subdomains from Chaos, pipe to subfinder for further enumeration
chaos -d target.com -silent | subfinder -silent | httpx -silent
Chaos gives you a seeded list of known in-scope subdomains. Subfinder and similar tools expand from there. This is faster than starting enumeration from scratch on a programme you haven't touched before.
For researchers running tooling across many programmes simultaneously, Chaos provides a structured way to keep your target list current without manually scraping each programme's scope page.

Practical Limitations
A few things to keep in mind:

Chaos doesn't cover private programme scopes, only public ones
Update frequency varies; some entries lag the source programme by days or weeks
Wildcard scope entries (*.example.com) require your own subdomain enumeration on top - Chaos lists the wildcard, not every valid subdomain
Not all platforms are equally well-represented; H1 public programmes tend to be the most complete


Related

HackerOne
Bugcrowd
Intigriti
Competition Assessment
New Program Strategy
