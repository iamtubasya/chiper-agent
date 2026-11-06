# PDF Report Generation with Embedded Screenshots

After finding vulnerabilities, generate professional PDF reports per-finding with embedded PoC screenshots.

## Workflow
1. **Generate terminal-style screenshots** with PIL/Pillow (dark theme):
   - BG=(40,44,52), title bar with red/yellow/green dots
   - Monospace font: `C:/Windows/Fonts/consola.ttf` (Windows) or DejaVuSansMono
   - Render each PoC step as colored line (GREEN=command, RED=vulnerability, CYAN=headers)
   - Save as PNG, ~900px wide, auto-height
2. **Create individual PDFs** per finding with reportlab:
   - Cover → Severity → Description → Vulnerable Code → Repro Steps → **Screenshot** → Impact → Fix → Validation Gates
   - Use `Image(img_path, width=160*mm, height=100*mm)` to embed screenshots
   - Use `Preformatted(code, CodeBlock_style)` for code blocks with dark background
3. **Create combined report** with all findings + chain dependency matrix
4. **Create chain analysis report** — determines if findings are independent or chained

## reportlab Style Conflicts (PITFALL)
- DON'T reuse 'Code' — already exists in `getSampleStyleSheet()`
- Use unique names: 'CodeBlock', 'Body', 'FTitle', 'SevCrit'
- Default styles that COLLIDE: Code, Normal, Title, Heading1-6, List

## Terminal Screenshot Template
```python
from PIL import Image, ImageDraw, ImageFont
def render_terminal(lines, filename, title="Terminal"):
    W = 900; H = 40 + len(lines)*18 + 24
    img = Image.new('RGB', (W, H), (40,44,52))
    draw = ImageDraw.Draw(img)
    # Title bar
    draw.rectangle([(0,0),(W,28)], fill=(30,33,40))
    draw.ellipse([(10,9),(22,21)], fill=(255,95,87))  # red
    draw.ellipse([(28,9),(40,21)], fill=(255,189,46)) # yellow
    draw.ellipse([(46,9),(58,21)], fill=(39,201,63))  # green
    draw.text((70,6), title, fill=(108,112,134), font=font)
    y = 40
    for text, color in lines:
        draw.text((12, y), text, fill=color, font=font)
        y += 18
    img.save(filename, 'PNG')
```

## Chain Dependency Analysis
1. List each finding's entry point (what single input triggers it)
2. Check prerequisites (does finding X require finding Y?)
3. Classify: Independent (standalone) vs Chained (requires another finding)
4. Generate per-finding reports if independent, chain report if chained
5. Include dependency matrix table in combined report

## Windows-Specific Notes
- **Rust setup**: Download rustup-init.exe via curl, run `rustup-init.exe -y --profile minimal`
- **GNU toolchain**: If MSVC linker missing: `rustup toolchain install stable-x86_64-pc-windows-gnu` then `rustup default stable-x86_64-pc-windows-gnu`
- **Path handling**: Use `write_file` tool instead of heredoc in MSYS bash — heredocs with single quotes fail
- **Large scripts**: Split PDF generators into 3 files (data + generator + runner) to avoid write_file timeout at ~8KB

## Per-Finding Report Structure
```
COVER PAGE
  Target, Finding ID, Severity, CVSS, Type, Date, Auditor
SEVERITY
  CVSS vector, CWE, Type, Impact summary, Independence status
DESCRIPTION
  Detailed technical description
VULNERABLE CODE
  Extracted code block with line references
REPRODUCTION STEPS
  Numbered steps (minimum 5 per finding)
POC SCREENSHOT
  Embedded terminal-style PNG image
POC ANALYSIS
  Text explanation of what the screenshot shows
IMPACT
  Financial / DoS / manipulation impact with CVSS justification
RECOMMENDED FIX
  Code-level remediation with specific function/line references
VALIDATION GATES
  7-gate Stage 7 checklist (By-Design, Mitigated, Realistic, Impact, Independent, Verdict)
```
