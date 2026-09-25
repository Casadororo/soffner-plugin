---
name: full-review
description: Use ONLY when the user invokes `/full-review`, or asks for the full review sequence on a pull request (ponytail, super review, bug hunter, ponytail again). Runs the four reviews in order on the PR's branch and applies each review's fixes before the next one starts, so every review reads the code the previous one left. Never auto-triggers on a mere mention of a review.
---

# full-review

Four reviews over one PR, in a fixed order, with the fixes applied in between:

| # | Review | Runs as | Why there |
|---|--------|---------|-----------|
| 1 | `/ponytail:ponytail-review` | inline, no subagent | Cheap, and it shrinks the diff that the two expensive reviews will read |
| 2 | `/super-review-gate <pr>` | the gate's fan-out, evaluators on **Haiku** | Rule adherence. Each evaluator reads one rule against the diff: checklist reading, not the job for an expensive model |
| 3 | `/bug-hunter-gate <pr>` | the gate's three lenses in parallel, default model | Runtime bugs. Here the reasoning is the point, so the lenses keep the stronger model |
| 4 | `/ponytail:ponytail-review` | inline, no subagent | The two gates added code and regression tests. This pass cuts what they left behind |

**Fix between every review.** A review whose findings are not applied before the next one starts makes the next review read stale code and report the same things again. After each review: apply the fixes, run the affected tests, commit, push. Only then start the next review.

## Arguments

`/full-review [pr]`

| Token | Rule |
|-------|------|
| `pr` (optional) | `123`, `#123`, a PR URL or a branch name. Absent: the PR of the current branch. |

## What the invocation authorizes

Committing and pushing **on this PR's branch only**, as many times as the fixes need. The invocation is the explicit request the project asks for before a commit. Outside it: pushing to any other branch, merging, destructive database commands, starting a dev server, opening a browser.

## Before the first review

1. **Start in a fresh session.** Not the session that wrote the PR. A review that carries weeks of conversation pays for that context on every step, and it also carries what the author believes already works. If this session already has a long history, stop and tell the operator to open a new one.
2. **Be on the PR's branch.** `gh pr view <pr> --json number,headRefName,baseRefName,url`, then `git branch --show-current`. Different branch: run `/soffner:dono <pr>` and continue inside the worktree it lands in.
3. **Check the gates exist.** `/super-review-gate` and `/bug-hunter-gate` are project skills (V360 has them in `.claude/skills/`). Either one missing: say so and stop. Never replace a gate with its bare skill (`/super-review`, `/bug-hunter`): the bare `/super-review` fans out on the session model, and that Opus fan-out was the single largest token cost this skill exists to avoid.
4. **Uncommitted changes in the worktree.** Read them (`git diff`, `git diff --cached`). They are usually an earlier review cut short. Run the affected tests and commit them first, so every review starts from a clean tree.

## The sequence

### 1. Ponytail

Run `/ponytail:ponytail-review` over the PR diff (`gh pr diff <pr>`). Apply every `delete` / `yagni` / `shrink` / `stdlib` / `native` finding that does not change behavior, and repeat until it answers `Lean already. Ship.` Run the affected tests with the project's test command (V360: `bin/testq`, never `rails test` directly), commit, push. Note the `net: -N lines`.

### 2. Super review

`/super-review-gate <pr>`. Keep its default: the rule evaluators run on Haiku. The gate loops on its own: it fixes every theme below 4, fixes or justifies each 4, re-runs, and posts one verdict on the PR at the end. The fixes run in this session, and each iteration is committed and pushed before the next one.

Ping-pong (the same low score for 3 iterations in a row, with no evaluator saying what to change) points at a lost evaluator, not at bad code. Re-run once with `model=sonnet`, as the gate itself says. Still stuck: stop and report instead of spending the remaining iterations.

### 3. Bug hunter

`/bug-hunter-gate <pr>`. It hunts with three lenses in parallel, fixes Critical and High, fixes Medium and Low with a regression test or justifies them, re-hunts, and posts one verdict on the PR at the end. Every fix is committed and pushed before the next hunt.

### 4. Ponytail again

Same as step 1, over the final diff. Cut what the gates added and did not need, keep every regression test the bug hunter demanded, run the affected tests, commit, push.

## Economy

- Do not re-read the whole PR between steps. Each gate regenerates the diff on its own.
- A failing test is work to fix. A test run that fails on infrastructure (database down, pending migration, stale fixtures) is not: stop and report the exact error to the operator.
- No new tests beyond the regression tests the bug hunter gate requires.
- CI is out of scope. Report the last pushed commit and let the caller decide whether to watch the checks.

## Report

Print to the operator, in English:

```
## full-review: PR #<number> <title>

Ponytail (start): net -<N> lines
Super review: <iterations>, verdict <link>, justified: <list or none>
Bug hunter: <iterations>, <fixed> fixed, verdict <link>, justified: <list or none>
Ponytail (end): net -<N> lines
Last commit: <sha>
Stopped early: <why, or no>
```

The two verdicts the gates post on the PR follow the project's language (pt-BR in V360). That is the gates' payload, not this skill's source.
