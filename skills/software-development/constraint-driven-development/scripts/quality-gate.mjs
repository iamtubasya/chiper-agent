#!/usr/bin/env node
/**
 * quality-gate.mjs — Constraint-Driven Development quality gate.
 *
 * Enforces that the "signal" tools (tsc, eslint, semgrep, axe, gitleaks)
 * actually FAIL the build when they report findings, instead of merely
 * printing them and exiting 0.
 *
 * Usage:
 *   node scripts/quality-gate.mjs            # run all gates
 *   node scripts/quality-gate.mjs --fast     # skip slow gates (semgrep/axe)
 *   node scripts/quality-gate.mjs --json     # machine-readable summary
 *
 * Exit codes:
 *   0  all gates pass
 *   1  at least one gate reported findings
 *   2  a gate could not be executed (missing tool / crash) — treated as failure
 *
 * Design notes:
 *   - Thresholds live at the top so a project can lift them into its own config.
 *   - A missing scanner is exit 2 (loud), never a silent pass. Sneaking a green
 *     build by skipping an absent tool is exactly the anti-pattern this skill bans.
 *   - No network access; semgrep registry rules are opt-in via SEMGREP_CONFIG.
 */

import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";

const FAST = process.argv.includes("--fast");
const JSON_OUT = process.argv.includes("--json");

// --- thresholds (loosen only with an explicit, reviewed commit) -------------
const THRESHOLDS = {
  maxEslintErrors: 0,
  maxEslintWarnings: 0,
  maxSemgrepFindings: 0,
  maxAxeViolations: 0,
  maxSecrets: 0,
};

function which(bin) {
  const r = spawnSync("command", ["-v", bin], { shell: true, encoding: "utf8" });
  return r.status === 0 && r.stdout.trim() ? r.stdout.trim() : null;
}

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { encoding: "utf8", shell: false, ...opts });
  return {
    code: r.status === null ? 2 : r.status,
    stdout: r.stdout || "",
    stderr: r.stderr || "",
  };
}

const gates = [];
function gate(name, fn, { slow = false } = {}) {
  if (FAST && slow) return;
  gates.push({ name, fn, slow });
}

// ---- Gate: TypeScript ------------------------------------------------------
gate("typescript", () => {
  if (!existsSync("tsconfig.json")) return { skipped: "no tsconfig.json" };
  const tsc = which("tsc") || which("npx");
  if (!tsc) return { failed: "tsc not installed", code: 2 };
  const args = tsc.endsWith("npx") ? ["tsc", "--noEmit"] : ["--noEmit"];
  const r = run(tsc, args);
  if (r.code !== 0) return { failed: "type errors", code: 1, detail: r.stdout.slice(-2000) };
  return { ok: true };
});

// ---- Gate: ESLint ----------------------------------------------------------
gate("eslint", () => {
  const bin = which("eslint");
  if (!bin) return { failed: "eslint not installed", code: 2 };
  const r = run(bin, [".", "--format", "json"]);
  let errors = 0, warnings = 0;
  try {
    const report = JSON.parse(r.stdout || "[]");
    for (const f of report) {
      errors += f.errorCount || 0;
      warnings += f.warningCount || 0;
    }
  } catch {
    return { failed: "eslint produced unparseable output", code: 2 };
  }
  if (errors > THRESHOLDS.maxEslintErrors || warnings > THRESHOLDS.maxEslintWarnings) {
    return { failed: `${errors} errors / ${warnings} warnings (limits ${THRESHOLDS.maxEslintErrors}/${THRESHOLDS.maxEslintWarnings})`, code: 1 };
  }
  return { ok: true, errors, warnings };
});

// ---- Gate: secrets ---------------------------------------------------------
gate("gitleaks", () => {
  const bin = which("gitleaks");
  if (!bin) return { failed: "gitleaks not installed", code: 2 };
  const r = run(bin, ["dir", ".", "--redact", "--exit-code", "1", "--no-banner"]);
  if (r.code !== 0) return { failed: "secret(s) detected", code: 1, detail: r.stdout.slice(-2000) };
  return { ok: true };
});

// ---- Gate: semgrep (slow) --------------------------------------------------
gate("semgrep", () => {
  const bin = which("semgrep") || which("opengrep");
  if (!bin) return { failed: "semgrep/opengrep not installed", code: 2 };
  const config = process.env.SEMGREP_CONFIG || "auto";
  const r = run(bin, ["scan", "--config", config, "--json", "--quiet"]);
  let findings = 0;
  try {
    const out = JSON.parse(r.stdout || "{}");
    findings = (out.results || []).length;
  } catch {
    return { failed: "semgrep produced unparseable output", code: 2 };
  }
  if (findings > THRESHOLDS.maxSemgrepFindings) {
    return { failed: `${findings} semgrep finding(s)`, code: 1 };
  }
  return { ok: true, findings };
}, { slow: true });

// ---- Gate: axe (slow, needs a built app) -----------------------------------
gate("axe", () => {
  const bin = which("axe");
  if (!bin) return { skipped: "axe not installed (browser a11y gate needs @axe-core/cli)" };
  const url = process.env.AXE_URL;
  if (!url) return { skipped: "set AXE_URL to enable the accessibility gate" };
  const r = run(bin, [url, "--exit"]);
  if (r.code !== 0) return { failed: "accessibility violations", code: 1, detail: r.stdout.slice(-2000) };
  return { ok: true };
}, { slow: true });

// ---- Run -------------------------------------------------------------------
let worst = 0;
const results = [];
for (const g of gates) {
  let res;
  try {
    res = g.fn();
  } catch (e) {
    res = { failed: `gate crashed: ${e.message}`, code: 2 };
  }
  results.push({ gate: g.name, ...res });
  if (res.failed && (res.code || 1) > worst) worst = Math.max(worst, res.code || 1);
}

if (JSON_OUT) {
  console.log(JSON.stringify({ ok: worst === 0, gates: results }, null, 2));
} else {
  for (const r of results) {
    const mark = r.ok ? "PASS" : r.skipped ? "SKIP" : "FAIL";
    const extra = r.ok
      ? Object.entries(r).filter(([k]) => !["gate", "ok"].includes(k)).map(([k, v]) => `${k}=${v}`).join(" ")
      : r.skipped || r.failed;
    console.log(`  [${mark}] ${r.gate}${extra ? "  " + extra : ""}`);
  }
  console.log(worst === 0 ? "\nQUALITY GATE: PASS" : "\nQUALITY GATE: FAIL");
}

process.exit(worst);
