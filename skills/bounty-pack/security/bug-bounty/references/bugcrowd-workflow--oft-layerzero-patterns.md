# LayerZero V2 OFT — Vulnerability Patterns

## Architecture Overview
- **OFT (Omnichain Fungible Token):** ERC20 + LayerZero messaging for cross-chain transfers
- **lzReceive:** Called by LZEndpoint on destination chain to process cross-chain messages
- **lzReceiveAndRevert:** Same but reverts on failure (batch receive with rollback)
- **setPeer:** Owner-only function to set trusted cross-chain peer address
- **setEnforcedOptions:** Owner-only function to set mandatory message options per chain

## Key Functions to Audit

### lzReceive (CRITICAL entry point)
```
- Validates: msg.sender == LZEndpoint (OnlyEndpoint)
- Validates: peer exists (NoPeer error)
- Validates: peer matches sender (OnlyPeer error)
- Mints tokens on destination chain
- Optionally calls endpoint for callback
```

### setPeer (CRITICAL admin function)
```
- Owner-only (OwnableUnauthorizedAccount)
- Sets mapping[chainId] = peerAddress
- Can be hijacked if owner key compromised
- Consider: is there a timelock? multisig?
```

## Common Vulnerability Patterns

### 1. Cross-Chain Message Replay
**Risk:** Same lzReceive message submitted twice (once per chain)
**Check:** Does lzReceive track nonce per (srcChainId, srcAddress)?
**Check:** Is the message hash validated against storage?

### 2. Peer Validation Bypass
**Risk:** Attacker sets malicious peer → mints tokens on any chain
**Check:** Is setPeer behind onlyOwner?
**Check:** Is there a timelock or multisig?
**Check:** Can delegatecall to this contract bypass access control?

### 3. Missing Source Chain Validation
**Risk:** Message from wrong chain processed as if from valid peer
**Check:** Does lzReceive validate _srcChainId against expected value?

### 4. Token Mint/Burn Logic Errors
**Risk:** Incorrect amount minted (decimal conversion error, overflow)
**Check:** decimalConversionRate calculation (sharedDecimals → local decimals)
**Check:** Amount masking in lzReceive (uint64 extraction from msg.data)

### 5. Callback Injection
**Risk:** lzReceive calls external contracts with attacker-controlled data
**Check:** Is the callback data validated?
**Check:** Can callback be used to drain approvals?

### 6. EnforcedOptions Manipulation
**Risk:** Owner sets options that break cross-chain flow
**Check:** Can enforcedOptions be used to grief legitimate transfers?
**Check:** Is the options format validated?

## Decompiled Code Analysis Tips
- Unknown functions in decompiled OFT code often map to:
  - `quoteOFT` → pricing for cross-chain transfer
  - `lzReceive` → message processing
  - `setPeer` → peer configuration
  - `quoteSend` → send pricing
  - `isComposeMsgSender` → compose message validation
  - `send` → initiate cross-chain transfer
  - `lzReceiveSimulate` → simulation for preCrime
  - `allowInitializePath` → path initialization check
- Use selector database (4byte.directory) + bytecode analysis to resolve
