# PortSwigger WSA — File Upload
Source: https://portswigger.net/web-security/file-upload

## Technique headings
- File upload vulnerabilities
- Labs
- What are file upload vulnerabilities?
- What is the impact of file upload vulnerabilities?
- How do file upload vulnerabilities arise?
- How do web servers handle requests for static files?
- Exploiting unrestricted file uploads to deploy a web shell
- Web shell
- Exploiting flawed validation of file uploads
- Flawed file type validation
- Preventing file execution in user-accessible directories
- Insufficient blacklisting of dangerous file types
- Overriding the server configuration
- Obfuscating file extensions
- Flawed validation of the file's contents
- Exploiting file upload race conditions
- Race conditions in URL-based file uploads
- Exploiting file upload vulnerabilities without remote code execution
- Uploading malicious client-side scripts
- Exploiting vulnerabilities in the parsing of uploaded files
- Uploading files using PUT
- How to prevent file upload vulnerabilities
- Find file upload vulnerabilities using Burp Suite


## Labs (2026-10-18 — per-lab scenarios & solutions), 6 lab)

- **Remote code execution via web shell upload** (`lab-file-upload-remote-code-execution-via-web-shell-upload`)
  - Solution • While proxying traffic through Burp, log in to your account and notice the option for uploading an avatar image. • Upload an arbitrary image, then return to your account page. Notice that a preview of your avatar is now displayed on the page. • In Burp, go to Proxy > HTTP history . Click the filter bar to open the HTTP history filter window. Under Filter by MIME type , enable the Images checkbox, then apply your changes. • In the proxy history, notice that your image was fetched using a GET request to /files/avatars/<YOUR-IMAGE> . Send this request to Burp Repeater. • On your system
- **Web shell upload via Content-Type restriction bypass** (`lab-file-upload-web-shell-upload-via-content-type-restriction-bypass`)
  - Solution • Log in and upload an image as your avatar, then go back to your account page. • In Burp, go to Proxy > HTTP history and notice that your image was fetched using a GET request to /files/avatars/<YOUR-IMAGE> . Send this request to Burp Repeater. • On your system, create a file called exploit.php , containing a script for fetching the contents of Carlos's secret. For example: . <?php echo file_get_contents('/home/carlos/secret'); ?> • Attempt to upload this script as your avatar. The response indicates that you are only allowed to upload files with the MIME type image/jpeg or image/png
- **Web shell upload via path traversal** (`lab-file-upload-web-shell-upload-via-path-traversal`)
  - Solution • Log in and upload an image as your avatar, then go back to your account page. • In Burp, go to Proxy > HTTP history and notice that your image was fetched using a GET request to /files/avatars/<YOUR-IMAGE> . Send this request to Burp Repeater. • On your system, create a file called exploit.php , containing a script for fetching the contents of Carlos's secret. For example: . <?php echo file_get_contents('/home/carlos/secret'); ?> • Upload this script as your avatar. Notice that the website doesn't seem to prevent you from uploading PHP files. • In Burp Repeater, go to the tab contai
- **Web shell upload via obfuscated file extension** (`lab-file-upload-web-shell-upload-via-obfuscated-file-extension`)
  - Solution • Log in and upload an image as your avatar, then go back to your account page. • In Burp, go to Proxy > HTTP history and notice that your image was fetched using a GET request to /files/avatars/<YOUR-IMAGE> . Send this request to Burp Repeater. • On your system, create a file called exploit.php , containing a script for fetching the contents of Carlos's secret. For example: . <?php echo file_get_contents('/home/carlos/secret'); ?> • Attempt to upload this script as your avatar. The response indicates that you are only allowed to upload JPG and PNG files. • In Burp's proxy history, fi
- **Remote code execution via polyglot web shell upload** (`lab-file-upload-remote-code-execution-via-polyglot-web-shell-upload`)
  - Solution • On your system, create a file called exploit.php containing a script for fetching the contents of Carlos's secret. For example: . <?php echo file_get_contents('/home/carlos/secret'); ?> • Log in and attempt to upload the script as your avatar. Observe that the server successfully blocks you from uploading files that aren't images, even if you try using some of the techniques you've learned in previous labs. • Create a polyglot PHP/JPG file that is fundamentally a normal image, but contains your PHP payload in its metadata. A simple way of doing this is to download and run ExifTool f
- **Web shell upload via race condition** (`lab-file-upload-web-shell-upload-via-race-condition`)
  - Hint The vulnerable code that introduces this race condition is as follows: . <?php $target_dir = "avatars/"; $target_file = $target_dir . $_FILES["avatar"]["name"]; // temporary move move_uploaded_file($_FILES["avatar"]["tmp_name"], $target_file); if (checkViruses($target_file) && checkFileType($target_file)) { echo "The file ". htmlspecialchars( $target_file). " has been uploaded."; } else { unlink($target_file); echo "Sorry, there was an error uploading your file."; http_response_code(403); } function checkViruses($fileName) { // checking for viruses ... } function checkFileType($fileName) 
