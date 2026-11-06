# Ruby YAML deserialization — safe_load vs unsafe_load detection

When a Rails/Ruby app accepts a form field it also treats as YAML (classic example: a CSV/spreadsheet
importer's `columns_attributes[N][values]` submitted as `"---\n- Alice\n- Bob\n"`), prove the
deserialization path in three steps BEFORE reaching for an RCE gadget. Blindly firing the elttam
`Gem::Requirement` gadget wastes requests and produces false "not vulnerable" reads.

## 1. Is the field actually parsed AND used?

Submit a valid YAML array whose values DIFFER from the fallback source, e.g. values = `"---\n- Charlie\n"`
while the CSV holds "Alice". Then read the rendered/returned result:

- Result shows "Charlie" → the field is YAML-parsed and its output is CONSUMED (real attack surface).
- Result shows "Alice" (fallback) → the field is ignored, or its parse is rescued away. Stop.

## 2. safe_load vs unsafe_load — the object-tag signature

Inject two tags and compare the response:

- `--- !ruby/object:Random` (no-arg, benign class).
  - `YAML.safe_load` → raises `Psych::DisallowedClass` → controller rescues → field falls back to
    default = clean 302 + fallback value (Random is NOT instantiated / not usable).
  - `YAML.unsafe_load`/`YAML.load` → actually instantiates a Random object (would appear in the
    result as `#<Random:0x...>` or crash downstream).
- `--- !ruby/object:Gem::Requirement` (nested mapping that needs args/`init_with`).
  - If this returns **500 while `Random` returned a clean 302**, the parser IS instantiating
    objects by tag = `unsafe_load`, and the 500 is `NoMethodError`/`init_with` failure during
    instantiation — the RCE-deserialization signature, NOT a safe_load rejection.
- Malformed `::: not yaml :::` → if this is an **unhandled 500** (Psych::SyntaxError not rescued),
  that is a separate low-severity "unhandled exception on user input" signal — distinct from the
  deserialization question.

## 3. Only escalate to a gadget if step 2 proves unsafe_load

If `!ruby/object:Random` fell back (safe_load), there is no object-instantiation primitive — do not
fire the gadget. If `!ruby/object:*` actually instantiated, use the universal Ruby gadget
(elttam): `Gem::Requirement` + `Gem::Package::TarReader` + `Net::WriteAdapter` + `Kernel.system`,
with `msg: "sleep 8"` as a time-based proof. Measure the response delta vs a plain YAML-array
baseline:

- +~8s response = RCE confirmed.
- Clean 500 with NO delay = the gadget chain itself is malformed (not RCE) — iterate the gadget
  structure, do not claim RCE from a plain 500.

## Observed (conferencebadge.com dash, 2026-11-01)

Spreadsheet-import `columns_attributes[0][values]` was YAML-parsed and its result USED ("Charlie"
overrode CSV "Alice"), but `!ruby/object:Random` fell back to the CSV value = `YAML.safe_load` →
not an RCE primitive. Malformed YAML (`::: not yaml :::`) surfaced an unhandled 500
(Psych::SyntaxError). Net finding: low-severity unhandled exception, NOT RCE.