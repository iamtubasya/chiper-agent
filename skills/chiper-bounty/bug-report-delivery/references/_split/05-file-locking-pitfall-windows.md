## File Locking Pitfall (Windows)

On Windows, if the PDF is open in a viewer (Adobe, Edge, Chrome), `open(path, "wb")` raises `PermissionError: [Errno 13]`.

**Workaround:**
```python
# Option 1: Save with temp name, then rename
temp_path = output_path.replace('.pdf', '-new.pdf')
doc.build(story, filename=temp_path)
os.replace(temp_path, output_path)  # atomic rename

# Option 2: Catch and save with alternative name
try:
    doc.build(story)
except PermissionError:
    alt_path = output_path.replace('.pdf', '-v2.pdf')
    doc.build(story, filename=alt_path)
    print(f"Original locked. Saved to: {alt_path}")
```

**Never block on this** — just save with a different filename and tell the user.

