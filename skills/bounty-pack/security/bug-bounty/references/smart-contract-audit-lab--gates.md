# Validation Gates — Detailed Criteria

## Gate 1: By-Design Check

### Questions to Ask
1. Is this behavior documented in the contract comments?
2. Would the developer say "yes, that's how it works"?
3. Is this standard practice in similar protocols?
4. Does the protocol's documentation describe this as intended?

### Verification Steps
1. Read all contract comments and documentation
2. Check if the "vulnerability" is mentioned in the codebase
3. Compare with similar protocols (is this standard?)
4. Ask: "If I remove this behavior, does the protocol still work?"

### Decision Rule
If the answer to any question is "yes" → **FAIL** (by design)

---

## Gate 2: Mitigation Check

### Questions to Ask
1. Does Solidity atomicity prevent the attack?
2. Is there an access control check that blocks it?
3. Do economic incentives prevent the attack?
4. Does the attack require external dependencies (off-chain systems)?
5. Is there a timelock that prevents immediate exploit?

### Verification Steps
1. Trace the complete attack path (every step)
2. Check if any step reverts (atomicity)
3. Check if any step is access-controlled
4. Check if the attack is economically rational for attacker
5. Verify the attack works on a fork (not just theory)

### Decision Rule
If ANY mitigation exists → **FAIL** (mitigated)

---

## Gate 3: Realistic Exploitation Check

### Questions to Ask
1. Can an attacker execute this without extraordinary conditions?
2. Does the attacker profit (not just cause damage)?
3. Are all preconditions realistic (not theoretical)?
4. Is the attack deterministic (not dependent on market conditions)?

### Verification Steps
1. Write the complete attack scenario (step by step)
2. Identify ALL preconditions
3. Verify each precondition is realistic
4. Confirm the attacker profits (not just causes damage)
5. Test on fork to verify it works

### Decision Rule
If ANY precondition is unrealistic → **FAIL** (unrealistic)

---

## Gate 4: Impact Check

### Questions to Ask
1. Are there real funds at risk?
2. Who loses money (quantify)?
3. Is the loss material (not dust amounts)?
4. Is there a financial incentive for the attacker?

### Verification Steps
1. Quantify funds at risk (exact amount)
2. Identify the victim (who loses money)
3. Verify the loss is material (>$100 minimum)
4. Confirm the attacker profits (not just causes damage)

### Decision Rule
If no real measurable harm → **FAIL** (no impact)
