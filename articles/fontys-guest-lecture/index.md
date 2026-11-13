---
title: How Much Coverage Is Enough?
summary: I gave a guest lecture on mutation testing to third-year ICT students at Fontys in Strijp-S, the first ICT guest lecture there this year. How I built it, and the presentation tricks I borrowed from Veritasium.
author: Kieran van der Heijde
avatar: assets/kieran.jpg
date: 2026-10-29
featured: true
---

On 29 October I gave a guest lecture at Fontys University of Applied Sciences in Strijp-S, to third-year ICT students in semesters 6 and 7. The topic was mutation testing, and how I made it fast enough to use in [Angelo](https://angelo.kcvdh.com).

Two things made it special. It was the first ICT guest lecture at Fontys this year; they told me they had more or less stopped doing them. And afterwards they asked me to come back for another one.

## The goal

Mutation testing sounds like a research topic. It is very specific, and on paper it is complex. I wanted to show students two things: what it is and why it matters, and the engineering process behind Angelo. Things can look incredibly complex, but with the right mindset and by dumbing them down, you can still do a lot.

## Borrowing from Veritasium

Veritasium videos keep you watching because they never just hand you an answer. I built the deck around four of their habits.

**1. Open with a question, not a topic.** The first slide was not "Mutation testing". It was *How much test coverage is enough?* Everyone in the room has an answer to that, usually a percentage. That is the point.

**2. Make it real with a story.** Before any theory, one line of code:

```c
MD_Update(&m, buf, j);
```

In 2006 this line was commented out of Debian's OpenSSL. The tests still passed, and every SSL key generated on Debian and Ubuntu was suddenly no longer random. Mutation testing would have shown that removing this line was untested.

**3. Break the belief before teaching the fix.** Next came a quote from Inozemtseva and Holmes (ICSE 2014): *"high levels of coverage do not indicate that a test suite is effective."* Only once the old answer was gone did I ask *How do you know your test suite is effective?*, and then showed mutation testing on one line:

| Mutant | Result |
| --- | --- |
| `if (a >= b)` | Killed, a test failed |
| `if (a < b)` | Killed, a test failed |
| `// if (a > b)` | Survived, all tests still pass |

Mutation coverage: 2 / 3 = 67%.

**4. One idea per slide, as a question.** Almost every slide was a single question, with the answer only spoken: *What mutation coverage should you aim for?* (You shouldn't aim for one; use it to find lines that look tested but aren't.) *You must run the test suite for every mutation, right?* (You don't.)

And like a good video, it ended where it started. The last slide asked *How much test coverage is enough?* again. This time the answer was: wrong question. The real question is how many future mistakes your tests will catch.

## Showing the process

The middle of the lecture was hands-on. Students installed [Cosmic Ray](https://github.com/sixty-north/cosmic-ray) or Angelo and tried mutation testing on their own, while I walked around to answer questions.

Then the problem: mutation testing is slow. You run the full test suite once for every mutant, and a codebase easily has thousands. As the creator of Angelo, how did I speed that up? I walked through three steps, each one a question first:

- **Law of large numbers:** you don't need every mutant to know the score. A sample is enough. ([docs](https://angelo.kcvdh.com/06-operators-and-sampling/))
- **Some mutations will error:** if you know beforehand, why run them, and why count them? ([docs](https://angelo.kcvdh.com/02-test-selection/))
- **One run per mutant?** Not if you know which tests reach which mutant. ([docs](https://angelo.kcvdh.com/01-batch-mutating/), and the full story in [Eight Bugs, One Test Run](/articles/batch-mutation-testing/))

I closed with my own opinion on the future: small AI models are getting faster and smarter, and they can generate complex mutations from context. Mutation testing will become less deterministic, but I expect the overall quality to improve.

## Why I did it

I found it really cool to share knowledge on something this specific. I'm a self-taught engineer, and showing my process step by step was the point: none of these steps is hard on its own. I hope it inspires a few students to pick a problem that looks too complex, and start dumbing it down.
