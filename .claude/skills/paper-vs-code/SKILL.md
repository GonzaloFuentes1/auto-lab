---
name: paper-vs-code
description: Cross-check a paper's stated theory/equations/algorithm against its official code release, to catch gaps between what's claimed and what's actually implemented. Use when the user gives a paper (PDF or arXiv link) plus its GitHub repo, asks "does the code actually match the paper", wants prior art verified before building on it, or wants a related-work claim double-checked before citing it.
---

# Paper vs. code

Why this exists: this project already hit exactly the failure mode this skill guards against — an
early implementation of a quasimetric formula (`iqe.py`) was written from memory of the paper
(Wang & Isola 2022) and silently did NOT have the triangle-inequality guarantee it claimed, caught
only by a direct numerical test (0/2000 → 490/2000 violations once actually checked). Don't trust
a paper's description or your own memory of a method — check the actual released code, and verify
numerically wherever that's cheap.

## Inputs needed

- The paper: a PDF (user-provided path, or fetch from arXiv if given a link/ID — arXiv abstract
  pages link directly to a PDF).
- The code: a GitHub URL. If the user only names the paper, search for "<paper title> github
  official implementation" before assuming there isn't one.

## Workflow

1. **Read the paper's method section first**, not the whole paper. Use the `Read` tool's `pages`
   parameter to target the method/algorithm/equations section rather than ingesting all 20+ pages
   at once (cheaper, and you don't need the related-work/intro prose for this task).
2. **Extract the concrete, checkable claims**: equations, pseudocode, specific hyperparameters,
   architectural details, loss functions. Write these down as a short list before touching the
   code — this is the same discipline as registering a hypothesis prediction before running the
   experiment (see `log-finding` skill): decide what you're checking before you look, so you're
   not rationalizing a match after the fact.
3. **Locate the implementation, targeted, not exhaustive.** Shallow-clone the repo
   (`git clone --depth 1 <url>`) into your scratchpad, then grep for the specific
   function/class/equation names from step 2 — don't read the whole repo. For a large or
   unfamiliar repo, delegate this step to the `Explore` agent with a specific question per claim
   ("where is the KL term from eq. 4 implemented?") rather than browsing manually in the main
   session — keeps raw file dumps out of context.
4. **Verify numerically where it's cheap**, not just by reading. If a claim is checkable with a
   small script (e.g. "this distance satisfies the triangle inequality", "this loss reduces to
   the stated form under X"), write a short test rather than trusting that the code looks right.
   Reading code and running it can disagree — this is exactly what caught the `iqe.py` bug.
5. **Report as a table**, most important mismatches first:

   | Paper claim (§/eq.) | Code location | Match? | Notes |
   |---|---|---|---|
   | Eq. 4: quasimetric via max-mean potential | `model.py::IQEDistance.forward` | ✅ | Verified numerically, 0/5000 triangle-inequality violations |
   | "trained with batch size 4096" | `configs/base.yaml` | ⚠️ partial | Repo default is 2048, paper's 4096 only in the appendix's scaling-law run, not the main config |

6. **Log what you found.** If this was done to ground a hypothesis before registering it, this
   *is* the literature-grounding step (see the autonomous research agent's step 1) — log a
   `citation` entry with real BibTeX, and note any confirmed-vs-paper discrepancy in the
   hypothesis's `prior_art` field so it's not silently forgotten by the time the paper gets
   written. If it surfaces something that changes a design decision, log a `decision_log` entry.

## What NOT to do

- Don't summarize the whole paper — this skill is about the specific claims relevant to what
  you're building, not a general paper summary.
- Don't assume "the code is the ground truth" either — code drifts from papers too (stale
  defaults, since-fixed bugs, ablations that were never merged back to main). Report the
  discrepancy, don't silently pick a side.
- Don't clone huge repos wholesale into the main session's context — shallow clone, targeted grep,
  delegate broad exploration to `Explore`.
