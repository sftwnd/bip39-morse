# Security Policy

`bip39-morse` is a tool that converts user-supplied entropy (typed as Morse
code) into a BIP39 mnemonic. The output is directly usable as a wallet seed.
Security issues are therefore treated with priority.

## Supported versions

The project is post-1.0; only the latest released minor version on `master`
receives security fixes. Older tags are not maintained.

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | yes                |
| < 1.0   | no                 |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security reports.**

Use one of these private channels:

1. **GitHub private vulnerability reporting** — preferred. Open
   <https://github.com/sftwnd/bip39-morse/security/advisories/new> and
   submit a draft advisory.
2. **Email** — `sftwnd@gmail.com` with subject prefix `[bip39-morse
   security]`. PGP welcome on request.

Please include:

- A description of the issue and its impact (what an attacker gains).
- Reproduction steps or a minimal proof of concept.
- Affected version / commit.
- Any suggested mitigation, if you have one.

I will acknowledge receipt within **3 working days** and aim to provide a
fix or remediation plan within **30 days** for confirmed issues. Reporters
are credited in the advisory unless they prefer to remain anonymous.

## In scope

- Bugs in `bitstream.py`, `bip39.py`, `morse.py`, or `reverse.py` that
  cause:
  - incorrect entropy → mnemonic derivation (mismatch vs BIP39 spec),
  - non-deterministic output for the same input,
  - silent truncation/extension of entropy,
  - any leakage of entropy or the mnemonic outside the process (logs,
    files, network, clipboard, environment).
- Round-trip failures (forward → reverse → forward must reproduce the
  same entropy hex; the documented checksum-recompute caveat on the last
  word does not count as a bug).
- Supply-chain issues in the dependency graph (`prompt_toolkit` and test
  extras).
- TUI behaviours that cause the typed phrase to persist in scrollback,
  history files, or be readable by other processes on the same host
  beyond what is inherent to running a terminal application.

## Out of scope

These are documented properties of the tool, not vulnerabilities:

- The user's host OS being compromised (covered by the *Security
  warning* in the README — use a clean live OS for real seeds).
- Weak entropy from a low-entropy typed phrase. The tool deliberately
  does not inject any randomness; the entropy quality is fully the
  user's responsibility.
- The phrase appearing in terminal scrollback before the process exits
  — this is inherent to TUI applications and noted in the README.
- Side-channels on the user's hardware (acoustic, electromagnetic,
  Recall-style screenshotting telemetry, etc.). These are addressed by
  the operational guidance in the README, not by the tool.
- Issues that require an attacker already having code execution on the
  host running the tool.

## Disclosure

I prefer **coordinated disclosure**: a fix is prepared and released
before the advisory is made public. For low-severity issues we can agree
on a shorter timeline; for high-severity issues affecting real seed
derivation, please give me up to 30 days before public disclosure.
