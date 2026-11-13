---
title: Eight Bugs, One Test Run
summary: Every mutation testing tool tests one mutant per run, for a good reason. Angelo tests eight at once without losing a single verdict. This is how it decides which mutants can share a run.
author: Kieran van der Heijde
avatar: assets/kieran.jpg
date: 2026-11-13
---

Every mutation testing tool follows one rule: one mutant, one test run. Five hundred mutants on a two-second suite is about seventeen minutes, and most of it is spent starting Python.

So why not plant ten mutants at once and cut the runs by ten? Because it quietly breaks the score, and the reason is worth a minute.

## Two bugs that cancel out

A mutant is a small change to your code. If a test fails, the mutant is *killed*; if every test passes, it *survived*. The method only works if each verdict belongs to exactly one change. Plant two mutants and that breaks:

```python
def is_valid(order):
    return order.total > 0           # mutant B: return not (order.total > 0)

def checkout(order):
    if not is_valid(order):          # mutant A: if is_valid(order):
        raise ValueError("empty order")
```

A test that expects `checkout(Order(total=0))` to raise kills A on its own, and kills B on its own. Run them together and B inverts the answer while A inverts the question. The inversions cancel, the code behaves like the original, and both mutants survive. The tests caught both bugs, and the tool reports that they caught neither.

This is **fault masking**. Polo, Piattini and García-Rodríguez (2009) paired mutants to halve the runs and accepted the lost verdicts. Angelo makes masking impossible instead.

## Masking needs a meeting point

A and B cancelled because one test executed both. Two mutants that no test ever runs together cannot hide each other. That gives the rule, and it is about the tests, not the source code:

> Two mutants **conflict** when the same test executes both. A **batch** is a set of mutants in which no two conflict.

## Step 1: which test runs which line

Angelo runs your suite once under coverage.py with one setting:

```ini
[run]
dynamic_context = test_function
```

Now coverage records not only *that* a line ran, but *which test* ran it. That gives a map from every line to its tests:

| | `test_dates` | `test_prices` | `test_checkout` | `test_valid` |
| --- | :---: | :---: | :---: | :---: |
| mutant A (`checkout`) | | | ✓ | |
| mutant B (`is_valid`) | | | ✓ | ✓ |
| mutant C (`parse_date`) | ✓ | | | |
| mutant D (`format_price`) | | ✓ | | |

A and B share `test_checkout`, so they conflict. The rest can mix. A mutant no test reaches survives without a run, and one that only runs at import time runs alone, because every test executes it.

## Step 2: pack the batches

Each mutant joins the first batch that accepts it. A batch keeps the union of its members' tests, so the check is one set comparison:

```rust
fn accepts(&self, mutant: &Mutant, covering: &HashSet<i64>, capacity: usize) -> bool {
    !self.covering_tests.is_empty()                  // import-time mutants stay alone
        && self.mutants.len() < capacity             // batch_size, 8 by default
        && self.covering_tests.is_disjoint(covering) // no shared test: no masking
        && !self.overlaps(mutant)                    // no two edits on the same bytes
}
```

On the table, that gives two batches: A, C and D together, and B alone. Four mutants, two runs. The last condition guards the file itself: a mutant that deletes `return a + b` and one that changes its `+` would corrupt each other's edits.

## Step 3: read the result

**Nothing fails:** every member ran all its tests with no one able to interfere, so every member survived. One run, many verdicts.

**Something fails:** each failed test is charged to the one member it covers. No two members share a test, so there is only one candidate:

```rust
for name in failed_tests {
    let test = self.context_id(&normalize(name))?;
    let mut explained = false;
    for (index, covering) in covering.iter().enumerate() {
        if covering.is_some_and(|tests| tests.contains(test)) {
            verdicts[index].1 = Status::Killed;
            explained = true;
        }
    }
    if !explained {
        return None; // nobody can explain this failure: do not guess
    }
}
```

**Anything else**, such as a crash or an unexplained failure: Angelo splits the batch in half and runs both halves, until every result is explained. A timeout is the exception: each member then runs alone, so the slow one is only waited out once. An odd result costs speed, never accuracy.

## Did it work?

Two hundred mutants, eight workers, a two-second suite:

| batch size | time | runs | score |
| --- | --- | --- | --- |
| 1 | 48.1 s | 161 | 39.5% |
| 8 | 10.4 s | 21 | 39.5% |

4.6 times faster, same score. Bigger batches barely help: on flask, 1,000 mutants pack into 409 batches with a cap of 8 and 407 with a cap of 32. Conflict, not the cap, is what limits a batch.

## The catch

This assumes your tests are independent. A batch runs the union of its members' tests, so a test that changes `os.environ` or the logging setup can change another member's verdict. On flask, batch sizes 8 and 1 disagree on 32 of 1,000 mutants. No packing can fix that; the tests share state, and batching only reveals it.

"One mutant per run" was never about mutants. It was about keeping two faults out of the same execution, and once you can see where every test goes, you can keep that promise eight at a time.

Angelo is open source: [github.com/kvandeh/Angelo](https://github.com/kvandeh/Angelo).
