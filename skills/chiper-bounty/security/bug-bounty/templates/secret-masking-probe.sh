#!/usr/bin/env bash
# Secret-masking probe ladder — paste as the body of a "Run a Script" step.
#
# Reference: references/secret-masking-control-testing.md
#
# Adapt the variable substitution syntax to the product:
#   Octopus Deploy / Azure DevOps-ish : #{VarName}
#   GitHub Actions / GitLab CI        : ${VARNAME}  (env-provided)
#   Jenkins                           : ${VARNAME} / %VARNAME%
#
# Define these variables in the project, ALL marked SENSITIVE:
#   L1=Z  L2=Zq  L3=Zqx  L4=Zqx9  L8=Zqx9Kp2m  L16=Zqx9Kp2mRt4wYh8n
#   S2  = ALPHASECRETLINE1<newline>BETASECRETLINE2
#   S3  = ONELINE1<newline>TWOLINE2<newline>THREELINE3
#   BIG = BIGSECRETVALUE0123456789
#   MID = MIDDLEVALUE-0123456789-ABCDEF
# Then read the task log back: GET /api/tasks/<id>/raw  (and /details, /details?verbose).
#
# INTERPRETATION
#   Anything below the masker's cut-off appears in cleartext -> length cut-off bug.
#   A full value masked but any partial (head/tail/cut/fold/embedded) cleartext -> exact-match-only bug.
#   Record the boundary (which length first masks) as the proof.

echo "=== 1. full value (baseline) ==="
echo "#{BIG}"

echo "=== 2. length ladder (find the cut-off) ==="
echo "L1=[#{L1}]"
echo "L2=[#{L2}]"
echo "L3=[#{L3}]"
echo "L4=[#{L4}]"
echo "L8=[#{L8}]"
echo "L16=[#{L16}]"

echo "=== 3. partial (single-line value) ==="
echo "P_cut20=[$(echo "#{MID}" | cut -c1-20)]"
echo "P_cut100_long=[$(echo "#{BIG}" | cut -c1-8)]"
echo "P_fold=[$(echo "#{MID}" | fold -w 10 | head -n 1)]"

echo "=== 4. embedded mid-line ==="
echo "P_mid=prefix-#{MID}-suffix"

echo "=== 5. multi-line, printed in full (usually masked) ==="
echo "#{S2}"
echo "#{S3}"

echo "=== 6. multi-line, PARTIAL (the high-impact case) ==="
echo "MP_first_of_2=[$(echo "#{S2}" | head -n 1)]"
echo "MP_two_of_3=[$(echo "#{S3}" | head -n 2)]"
echo "MP_last_of_3=[$(echo "#{S3}" | tail -n 1)]"
echo "MP_embedded=[x$(echo "#{S3}" | head -n 1)y]"

echo "=== 7. anchored-at-line-start partial (no shell wrapper) ==="
echo "#{S3}" | head -n 1
echo "#{S3}" | tail -n 1

echo "=== 8. product accessor path (second code path) ==="
# Octopus: get_octopusvariable <Name>   |  most CIs: just the env var
echo "[$(get_octopusvariable BIG 2>/dev/null || echo "#{BIG}")]"

echo "=== 9. padding then repeat (stream/chunk boundary) ==="
i=0; while [ $i -lt 150 ]; do echo "filler-$i-padding-padding-padding-padding"; i=$((i+1)); done
echo "AFTER_PADDING=[#{BIG}]"
echo "=== END ==="
