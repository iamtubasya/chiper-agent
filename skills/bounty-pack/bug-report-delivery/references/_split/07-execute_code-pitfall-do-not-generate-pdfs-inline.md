## ⚠️ `execute_code` Pitfall — DO NOT Generate PDFs Inline

`execute_code` (Python sandbox) frequently fails with **escape sequence errors** (`\\<` invalid escape) and **quote mismatches** in long multi-line strings containing XML/HTML/regex-heavy content (reportlab code blocks, curl command strings). These errors are silent until runtime and produce cryptic SyntaxWarning/SyntaxError.

### ⚠️ poc_text Type Flexibility Pitfall

When building PDFs with `reportlab`, PoC text may arrive as either a **string** or a **list of lines**. If your code calls `.split('\n')` on a list, it crashes with `AttributeError: 'list' object has no attribute 'split'`.

**WRONG — assumes string:**
```python
poc_text = get_poc_data()  # Could be list or string
lines = poc_text.split('\n')  # CRASH if list
```

**CORRECT — handle both:**
```python
poc_text = get_poc_data()
if isinstance(poc_text, list):
    lines = poc_text  # Already a list of lines
else:
    lines = poc_text.split('\n')  # Split string into lines
```

**Or normalize early:**
```python
poc_text = get_poc_data()
if not isinstance(poc_text, str):
    poc_text = '\n'.join(poc_text)  # Normalize to string
lines = poc_text.split('\n')
```

**WORKAROUND (mandatory for PDF generation):**
1. Write the full Python script to a `.py` file via `write_file`
2. Run it via `terminal` with the correct Python path

```python
# Step 1: Write script
write_file(path="~/project/gen_pdf.py", content=script_content)

# Step 2: Run it
terminal(command="/c/Users/WINDOWS10/AppData/Local/Python/bin/python.exe gen_pdf.py",
         workdir="~/project")
```

**Why not execute_code for PDF generation:**
- Long string literals with `\<`, `\n`, `\t`, `\"` cause SyntaxWarning/SyntaxError
- Platform content filtering also applies to execute_code scripts
- write_file + terminal isolates syntax errors to the file write step (lint catches them)

**When execute_code IS fine:**
- Short scripts with no complex string escaping
- Data processing (filter, transform, aggregate)
- Simple API calls with `requests`

