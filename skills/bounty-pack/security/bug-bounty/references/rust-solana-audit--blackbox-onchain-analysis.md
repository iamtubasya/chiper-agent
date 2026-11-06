# Black-Box On-Chain Program Analysis (No Source Code / No IDL)

For when you're auditing a deployed Solana program without access to the source code or IDL — e.g., game programs, closed-source DeFi, or when the GitHub repo is private.

## Phase 1: Transaction Enumeration

Get recent transactions interacting with the program:

```bash
# Get last 1000 signatures for the program
curl -s -X POST "https://api.mainnet-beta.solana.com" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getSignaturesForProgram",
       "params":["<PROGRAM_ID>", null, {"limit": 1000}]}'
```

Then fetch each transaction with `jsonParsed` encoding:
```bash
curl -s -X POST "https://api.mainnet-beta.solana.com" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getTransaction",
       "params":["<SIG>", {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}]}'
```

**Key fields to extract per transaction:**
- `transaction.message.accountKeys` — all accounts in the tx
- `transaction.message.instructions` — instruction accounts + programId + parsed data
- `meta.innerInstructions` — CPI calls (nested programs invoked)
- `meta.preTokenBalances` / `meta.postTokenBalances` — token balance changes per account
- `meta.logMessages` — program logs including instruction names

## Phase 2: Discriminator Mapping

Anchor programs use 8-byte discriminators: `SHA256("global:<InstructionName>")[0:8]`

**Step 1: Discover instruction names from logs.**
Search `meta.logMessages` for strings matching the pattern `Program log: <InstructionName>`.
Many Anchor programs log the instruction name before execution.

**Step 2: If names not in logs, extract raw discriminators.**
From `jsonParsed` instructions targeting the program, the `data` field contains base64-encoded instruction data.
The first 8 bytes of the decoded data are the discriminator.

```python
import hashlib
B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def sha256_disc(name):
    """Compute Anchor discriminator for an instruction name."""
    return hashlib.sha256(f"global:{name}".encode()).digest()[:8]

# Test candidate names
for name in ['deposit', 'withdraw', 'claim', 'swap', 'mint', 'burn']:
    disc = sha256_disc(name)
    print(f'{name}: {disc.hex()}')
```

**Step 3: Match discriminators to names.**
Compare computed SHA256 hashes against observed 8-byte prefixes.

## Phase 3: CPI Flow Analysis

**Inner instructions** reveal which programs are invoked via CPI:
```python
for ix in meta.get('innerInstructions', []):
    for inner in ix.get('instructions', []):
        if 'parsed' in inner:
            info = inner['parsed']
            print(f"  CPI: {info.get('type')} program={inner.get('programId')}")
            if info.get('info'):
                for k, v in info['info'].items():
                    print(f"    {k}: {v}")
```

**Critical check: CPI token transfers with 0 amount.**
If `innerInstructions` show a Token Program CPI with `amount: "0"` but `preTokenBalances`/`postTokenBalances` show actual balance changes, the program may be:
1. Using the CPI as validation (check account exists), with actual transfer via program-owned account manipulation
2. Using `updateAccountData` or similar low-level mechanism
3. The RPC parser may be misreporting the amount (check with base64 encoding)

## Phase 4: Account Structure Analysis

Map each instruction's account list:
```python
# From jsonParsed instruction
accounts = ix.get('accounts', [])
for i, acct in enumerate(accounts):
    role = "SIGNER+WRITABLE" if acct.get('isSigner') and acct.get('isWritable') else \
           "SIGNER" if acct.get('isSigner') else \
           "WRITABLE" if acct.get('isWritable') else "READONLY"
    print(f"  [{i}] {acct['pubkey'][:20]}... ({role})")
```

**Look for:**
- Constant accounts across all transactions → system PDAs (config, state, vault)
- Variable accounts → user-specific (wallets, token accounts, NFTs)
- Accounts NOT owned by the program → external dependencies (Token Program, System Program, Metaplex)
- Accounts owned by the program → program state (may contain encrypted/custom data)

**Check account ownership:**
```bash
curl -s -X POST "https://api.mainnet-beta.solana.com" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getAccountInfo",
       "params":["<ADDRESS>", {"encoding":"jsonParsed"}]}'
```
- `owner` field tells which program owns the account
- `executable` tells if it's a program itself
- `data` format depends on the owner program

## Phase 5: Transaction Simulation

Construct test transactions and simulate (no SOL cost, no signature verification):

**Tool:** `@solana/web3.js` (Node.js) — Python's solders is broken on 3.14+

```javascript
import { Connection, Keypair, VersionedTransaction, TransactionMessage } from '@solana/web3.js';

const connection = new Connection('https://api.mainnet-beta.solana.com');
const keypair = Keypair.generate(); // test wallet
const { blockhash } = await connection.getLatestBlockhash();

// Build instruction with forged discriminator + test payload
const ix = {
  keys: [/* account list */],
  programId: PROGRAM_ID,
  data: Buffer.from('DEADBEEFDEADBEEF' + '00'.repeat(31)), // fake discriminator + payload
};

const message = new TransactionMessage({
  payerKey: keypair.publicKey,
  recentBlockhash: blockhash,
  instructions: [ix],
}).compileToV0Message();

const tx = new VersionedTransaction(message);
const sim = await connection.simulateTransaction(tx, {
  sigVerify: false,              // skip signature check
  replaceRecentBlockhash: true,  // use provided blockhash
  accounts: { encoding: 'base64' },
});

console.log(sim.value.logs);     // program error messages
console.log(sim.value.err);      // error type
console.log(sim.value.unitsConsumed); // CU usage (0 = program never invoked)
```

**What simulation errors reveal:**
- `AccountNotEnoughKeys` → wrong number of accounts in instruction
- `InvalidProgramId` → wrong program ID or account ordering
- `Custom(<code>)` → program-specific error (check Anchor error codes)
- `0 CU consumed` → transaction rejected before program invocation (usually malformed tx structure)
- `InstructionError` → program rejected the instruction (check logs for details)

## Phase 6: Key Addresses Discovery

From transaction analysis, identify:
1. **Program ID** — the main program address
2. **Program Authority** — admin/signer for privileged operations
3. **Token Vault** — where program holds tokens (check Token account with program-related address)
4. **Game/Config State PDA** — global configuration account
5. **User State PDA** — per-user account derived from wallet address
6. **Token Mint** — the token/NFT mint address

**Derive PDAs:**
```python
from nacl.signing import SigningKey
import hashlib

def find_pda(seeds, program_id):
    """Find PDA for given seeds + program. Returns (address, bump)."""
    for bump in range(255, -1, -1):
        seed_data = b''.join(seeds) + bytes([bump])
        h = hashlib.sha512(seed_data).digest()
        point = bytearray(h[:32])
        point[0] &= 248
        point[31] &= 127
        point[31] |= 64
        # Check if NOT on ed25519 curve (valid PDA)
        try:
            SigningKey(bytes(point))
            continue  # valid key = not a PDA
        except:
            return bytes(point), bump
    return None, None
```

## Phase 7: Vulnerability Hypotheses

Common black-box Solana vulnerabilities:

### Transaction Manipulation
- **Account substitution** — Does the program validate that destination ATA belongs to the signer?
- **Amount manipulation** — Does the program trust instruction data amounts or verify on-chain balances?
- **Nonce bypass** — Is replay protection (IncNonce) enforced? Can operations skip it?

### Access Control
- **Missing signer check** — Are all required signers validated by the program?
- **PDA derivation check** — Does the program verify PDAs are correctly derived?
- **Authority confusion** — Can non-admin accounts call privileged instructions?

### Token Operations
- **Vault drain** — Can unauthorized withdrawals be constructed?
- **Free minting** — Can items/tokens be obtained without payment?
- **Price manipulation** — Can swap ratios be influenced?

### Front-Running / MEV
- **Sandwich attacks** — Are there price-oracle-dependent operations visible in mempool?
- **Front-running** — Can pending WithdrawV2Batch or DepositBatch txs be intercepted?
