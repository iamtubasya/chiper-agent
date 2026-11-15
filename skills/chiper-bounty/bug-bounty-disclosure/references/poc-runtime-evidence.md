# PoC sebagai bukti runtime — cetak nilainya, jangan cuma "ok"

Koreksi operator (2026-10-04): *"perbaiki pocnya supaya menjelaskan detail langkah2 reproduksi nya,
jgn hanya keterangan singkat, lengkapi dgn ss evidence"*.

Tes yang lulus tapi tidak mencetak apa pun bukan bukti bagi dev — hasilnya cuma `test ... ok`.
PoC yang baik **mencetak nilai yang dieksploitasi**: saldo sebelum→sesudah, record yang tersimpan,
counter yang di-nol-kan, jumlah 429 pada kontrol vs bypass. Screenshot dari transcript itulah
"ss evidence" yang diminta.

Pola umum tiap PoC: cetak `[1] … [n]` langkah + satu baris `RESULT: <klaim> = <bool>`, lalu `assert!`
yang sama. Transcript jadi bisa dibaca tanpa sumbernya.

## Rust / Soroban (`#![no_std]` contract tests)

`println!` tidak tersedia di crate `#![no_std]`. Tambahkan **`extern crate std;`** di header modul
test, lalu pakai `std::println!` — dan jalankan `cargo test … -- --nocapture`, kalau tidak outputnya
disembunyikan harness.

```rust
#![cfg(test)]
extern crate std;                       // <-- wajib, kalau tidak: cannot find macro `println`

use super::*;
```

```rust
std::println!("[1] UncollectedFees accrued = {}", accrued);
std::println!("[3] collect_fees() returned = {}", collected);
std::println!("RESULT: fee accounting wiped by non-admin = {}", collected == accrued && after == 0);
```

**`soroban_sdk::Address` tidak implement `Display`.** `{}` pada Address = gagal compile
`error[E0277]: soroban_sdk::Address doesn't implement core::fmt::Display`. Pakai **`{:?}`**:

```rust
std::println!("[2] NON-ADMIN {:?} calls collect_fees()", attacker);   // {} -> error, {:?} -> ok
```

Karena crate di-compile ulang per paket, **satu error format menggagalkan seluruh paket** — PoC lain
di crate yang sama ikut tidak jalan. Setelah menambah `println!`, jalankan tiap PoC satu per satu dan
pastikan tidak ada baris `error[` di transcript-nya sebelum bikin screenshot.

**Pitfall saat mem-patch header multi-attribute.** File seperti
```rust
#![cfg(test)]
#![allow(clippy::inconsistent_digit_grouping)]
```
bisa membuat patching string fuzzy menyisipkan `#![cfg(test)]` kedua di tengah file — inner attribute
di posisi itu = error. **Selalu baca ulang 5 baris pertama setelah mem-patch header `test.rs`.**

## Node / vitest

`console.log(...)` sudah cukup dan muncul di stdout runner. Jalankan **satu file PoC per perintah**
supaya transcript-nya bisa dipetakan 1:1 ke satu temuan:

```bash
npx vitest run __tests__/poc/poc-ratelimit-ip-spoof.test.ts > evidence/raw/TL-11.txt 2>&1
```

**Output vitest mengandung ANSI colour code** (`\x1b[33mtrue\x1b[39m`). Strip dulu
(`re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)`) sebelum memfilter/menyimpan — kalau tidak, filter
`startswith("PoC TL-")` tidak mengenai apa pun dan screenshot-nya kosong.

## Alur yang dipakai

```
raw/TL-XX.txt     satu transcript per temuan (cargo --nocapture / vitest run <file>)
   -> evidence/img/TL-XX.png      screenshot terminal (scripts/make_evidence.py di reportlab-security-pdf)
   -> PDF per temuan              langkah repro bernomor + cuplikan kode + screenshot tertanam
   -> 1 draft + 1 PDF + 1 PoC     per temuan (lihat aturan anti-slop §5)
```
