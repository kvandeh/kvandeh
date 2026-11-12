---
title: A mutation testing tool must never report a false score
summary: Angelo makes Python mutation testing up to 10.8 times faster. The difficult part was to keep the score true.
author: Kieran van der Heijde
avatar: assets/kieran.jpg
date: 2026-11-12
---

Mutation testing measures a test suite. The tool makes small changes to the code, called *mutants*, and runs the tests against each one. A mutant that makes a test fail is *detected*. The score is the percentage of detected mutants. The method is accurate, but slow.

A mutant is a small change of this type:

```python
def is_adult(age):
    return age >= 18   # original
    return age > 18    # mutant: a test with age == 18 must fail
```

[Angelo](https://github.com/kvandeh/Angelo) decreases a 48.1-second run to 4.5 seconds. It uses three methods: batching, test selection and warm worker processes. The score does not change. But each method also added a new way to report a false score.

```bash
pip install angelo-mut
angelo init                  # finds the project layout and writes angelo.conf
angelo exec --fail-under 60  # exits non-zero below 60%, so CI can gate on it
```

## Three failures

- **Path formats.** On Windows, coverage data used backslashes and Angelo used forward slashes. No path matched, so every mutant counted as untested. AlgoStudio scored 0.0%, and the run exited with success.
- **Plugins.** pytest-cov and pytest-xdist took over the coverage run. Again, no mutant matched, and the result was 0.0% with success.
- **Shared state.** A warm worker runs many mutants in one process. One mutant can change the working directory or the environment for the next. On the *click* library, this changed 44 of 1,000 verdicts.

The fix for the path formats was to normalise both sides before the comparison:

```rust
// coverage.py on Windows: src\pkg\mod.py   Angelo: src/pkg/mod.py
let key = path.replace('\\', "/");
```

## Rules

1. **A tool that cannot measure must not report success.** If coverage matches no mutant, Angelo stops with an error.
2. **A fast path can detect, but it cannot acquit.** Each mutant that a batch reports as survived runs again alone.
3. **Zero mutants is not a pass.** It is no information.

## Conclusion

The typical failure of a mutation testing tool is the failure that it finds in tests: a result that looks good but measures nothing. The speed came from the optimisations. The trust came from the checks around them.
