<!--
Thanks for the PR. Please fill in the sections below.

If this PR addresses a security vulnerability, STOP and read SECURITY.md
first — vulnerabilities should be reported privately, not opened as
public PRs against master.
-->

## Summary

<!-- 1-3 bullets: what changes and why. -->
-
-

## Type of change

<!-- Tick all that apply. -->
- [ ] Bug fix (no behaviour change for callers other than the bug being fixed)
- [ ] New feature (adds a new flag / mode / API surface)
- [ ] New Morse locale (file under `examples/`)
- [ ] Refactor (no behavioural change)
- [ ] Documentation only
- [ ] Test only
- [ ] CI / tooling

## Related issue

<!-- e.g. Closes #42 -->

## Test plan

- [ ] `pytest` passes locally with coverage ≥ 85% (the `fail_under` floor).
- [ ] If the bit pipeline / wordlist / morse tables were touched, a
      round-trip test is included (forward → reverse → forward
      reproduces the same entropy hex).
- [ ] For a new Morse locale: a round-trip test in
      `tests/test_morse_tables.py` exercises at least one decode/encode
      path through the new file.
- [ ] Manual smoke test of the affected CLI flags (paste command(s) used).

```
# commands you ran for the manual smoke test
```

## Documentation

- [ ] `README.md` updated (if user-visible behaviour changed).
- [ ] `README.ru.md` updated to match (if `README.md` was changed).
- [ ] `CHANGELOG.md` has an entry under `[Unreleased]`.
- [ ] For a new Morse locale: a row added to the table in the README's
      *Custom Morse tables* / *Latin accent extensions* section, with
      the standard cited.

## Security posture

<!--
For a project that handles seed material, even small changes can shift
the security model. Tick the box that applies.
-->
- [ ] This PR does **not** introduce: network calls, disk writes of
      entropy / phrase / mnemonic, clipboard writes, randomness
      injection, new runtime dependencies.
- [ ] This PR **does** introduce one of the above — justification is in
      the Summary, and a maintainer review is explicitly requested.

## Confirmations

- [ ] This PR contains no real BIP39 mnemonics, real entropy, or real
      wallet addresses anywhere (code, tests, comments, screenshots,
      commit messages).
- [ ] I have read [CONTRIBUTING.md](../blob/master/CONTRIBUTING.md) and
      [SECURITY.md](../blob/master/SECURITY.md).
- [ ] My commits follow the imperative-present style used in the
      project history (e.g. "Add ...", "Fix ...", "Refactor ...").
