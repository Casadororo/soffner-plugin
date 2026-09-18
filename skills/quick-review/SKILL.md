---
name: quick-review
description: Use when the user invokes `/quick-review`, or asks for a fast read of a pull request (uma revisada rapida, olha essa PR, vale a pena esse diff). One parallel wave of Sonnet lenses over the PR diff - bloat, dead tests, product holes, probable bugs - then every finding is weighed by whether fixing it buys anything real. Never auto-triggers on a mere mention of a PR, and never runs as a warm-up for another skill.
---

# quick-review

A **fast pass** over a pull request. One wave, four lenses, then a weighing step. It is not meant to be exhaustive — it is meant to be cheap enough to run on every PR and still be worth reading.

Two things make it fast, and both are deliberate:

- **One wave.** All lenses run in parallel and nothing runs after them. No Panel, no Judge, no second opinion. The orchestrator writes the output itself.
- **Burden of proof on the lens.** A finding arrives with the failure already named, or it gets cut. The orchestrator weighs findings, it does not investigate them.

The deliverable is a short table the author can act on in five minutes, plus one line saying whether the changed code looks correct.

**It reviews and stops.** No edits, no commits, no handing the findings to a skill that edits them. Whoever wrote the code fixes it, in their own session — this one only reports what it found. That separation is the entire reason to run the review somewhere other than the session that did the work, and it is gone the moment the reviewer starts patching what it just read.

**Depth is the other skill.** A full audit against `.claude/rules/`, with a Panel challenging every finding and inline comments on the PR, is `/soffner:self-review`. This skill does not read `.claude/rules/` at all — that is the split.

## Arguments

`/quick-review [pr]`

| Token | Rule |
|-------|------|
| `pr` (optional) | `123`, `#123`, a GitHub URL, or a branch name. Absent means the current branch's PR. |

Resolve the target before anything else:

```bash
gh pr view <pr-or-nothing> --json number,title,body,url,headRefName,changedFiles,additions,deletions
```

No PR for the current branch: fall back to the diff against the project's integration branch (the order its `CLAUDE.md` documents) via `git merge-base --fork-point`, and say in the header that the target is a raw diff. Everything else in the flow is identical.

**Size guard.** Over ~3000 changed lines or ~60 files, say so in one line before launching — a fast pass over a diff that size will miss things — and run anyway, unless the user narrows it. Do not silently truncate.

## The lenses

| Lens | Prefix | Reads for | Launched |
|------|--------|-----------|----------|
| Bloat | `BLOAT` | What in this diff did not need to exist | Always |
| Test Bloat | `TEST` | Which tests will never earn their CI time, and which changed behavior has no test at all | Only when the diff touches test files |
| Product | `PROD` | Where a real user of this feature falls over | Always |
| Implementation | `IMPL` | Whether the changed code is correct | Always |

Three lenses on a diff with no tests, four otherwise. Do not launch a lens with nothing to read.

## Subagent configuration

Every lens is launched with **`subagent_type: "general-purpose"` and `model: "sonnet"`** — the bare alias, which resolves to the newest Sonnet. Never inherit the session model, never Opus, never Haiku. All lens calls go in a **single message** so they run in parallel; a lens launched after the others defeats the point of the skill.

Effort stays default. This skill buys its value from four narrow readings, not from one deep one — if a finding needs deep thinking to hold up, it is a `/soffner:self-review` finding.

If a launch fails because `model` was rejected, retry with `claude-sonnet-5` and say so in the output. Never fall back silently to the session model.

## Phase 0 — context (cheap, do not skip)

1. **Diff to a file, never inline**: `gh pr diff <number> > /tmp/quick_review_diff.txt`
2. **Changed files to a file**: `gh pr diff <number> --name-only > /tmp/quick_review_files.txt`
3. **Diff stats**, for the header line: files changed, insertions, deletions (from the PR JSON, or `git diff --shortstat`).
4. **Intent**, inline and small: PR title + body as `{PR_INTENT}`. No PR: branch name plus `git log --oneline <base>..HEAD`. Nothing at all: `"(no stated intent)"`.
5. **Conventions**, inline: `CLAUDE.md`, if the project has one. Do **not** read `.claude/rules/`.
6. **Test files present?** Grep `/tmp/quick_review_files.txt` for the project's test paths — that decides whether the Test Bloat lens is launched.
7. Tell the user, in one line: `Quick review of PR #<n> — <files> files, +<add>/-<del> — <k> lenses.`

Do not read the changed files yourself. The lenses read from disk on demand.

## Phase 1 — the lenses, in parallel

Every lens gets the same template, with its own brief injected at `{LENS_BRIEF}`.

Bindings: `{LENS}` and `{PREFIX}` come from the lenses table, `{PR_INTENT}` and `{CLAUDE_MD}` from Phase 0. The diff is never inlined — the lens reads it from `/tmp/quick_review_diff.txt`.

---

**LENS AGENT PROMPT TEMPLATE:**

```
You are the {LENS} lens of a FAST review pass over a pull request. You have one job and a budget.

## Your job
{LENS_BRIEF}

## Budget — this is a fast pass, respect it
- Report AT MOST 5 findings. If you have more, report the 5 with the largest consequence and drop the rest.
- Read the diff, the changed files, and — only to confirm a specific finding — the definitions and callers that finding depends on.
- Do NOT run tests, do NOT start the app, do NOT install anything, do NOT audit files this PR did not touch, do NOT map the architecture.
- If confirming a finding would take more than a couple of file reads, drop the finding. Depth is another skill's job.

## Burden of proof — a finding without this is not a finding
Every finding must name a CONCRETE consequence: the input that breaks it, the user who hits it, the CI time it costs, the caller that goes wrong. "Could be a problem", "is cleaner", "is more idiomatic", "might confuse someone" are not consequences, and findings written that way get thrown out before the author ever sees them. Write nothing you cannot defend in one sentence.

## Scope
Only what this PR CHANGED. Pre-existing problems in untouched code are out of scope, however real.

## Author's intent
{PR_INTENT}

A change that matches the stated intent is not a finding just because it differs from the old behavior. A stated intent that the diff does NOT actually deliver is one of the best findings you can make.

## Out of bounds for every lens
Style, formatting, naming taste, import order, missing docs, "prefer this idiom". Not this skill.

## How to access the PR
- Diff: read `/tmp/quick_review_diff.txt`
- Changed files: read `/tmp/quick_review_files.txt`
- Any file you need: read it from the repository by path
Nothing is inlined in this prompt. Read it yourself.

## Project conventions
{CLAUDE_MD}

## Output — one block per finding, nothing else
### {PREFIX}-[N]: [short title]
- **Location:** [file:line, pointing at a changed line]
- **What is wrong:** [one or two sentences]
- **Consequence:** [the concrete failure — named input, named user step, named caller, or a CI cost]
- **What to do:** [one sentence, concrete]
- **Cost of doing it:** [small / medium / large, and why in a few words]
- **Confidence:** [confirmed in the code / probable / unverified]

End with: **{PREFIX} TOTAL: [N] findings**
If you found nothing worth the author's attention, say exactly `{PREFIX} TOTAL: 0 findings` and stop. An empty lens is a valid result — do not pad.
```

---

### `{LENS_BRIEF}` — Bloat (`BLOAT`)

```
Read this diff asking one question: what in here did not need to exist?

Hunt for:
- A file or helper that duplicates something the repo already has. Grep for the existing one before claiming it.
- An abstraction with exactly one user — interface, factory, service object, wrapper, config flag introduced for a single call site.
- A flag, setting or env var that nothing reads, or that is read in one place with a constant value.
- Dead on arrival: an unreachable branch, a parameter never passed non-default, an exported symbol nothing imports.
- Leftovers: commented-out code, debug logging, a TODO this PR already resolved, a fixture only the deleted code used.
- Churn mixed into a behavior change: reformatting, renames, import reshuffles that inflate the diff and the review cost without changing behavior.
- A dependency added for something an existing dependency or the standard library already does.

The bar: removal has to be SAFE and the cost of keeping it has to be REAL. If you cannot confirm nothing calls it, it is not a finding. "This feels unnecessary" is not a finding. Name what keeping it costs — review time now, a reader misled later, a config nobody will ever prune.

Deleting is also a change with a cost. A 200-line rewrite to remove one layer of indirection is rarely worth it in this PR. Say so in `Cost of doing it` instead of pretending it is free.
```

### `{LENS_BRIEF}` — Test Bloat (`TEST`)

```
Read the tests in this diff asking: which of these will never earn the CI time they cost, and which changed behavior is not covered at all?

Waste — hunt for:
- Tautologies: the test asserts a mock was called with what the test itself told it to call.
- Tests that restate the implementation line by line. Change the code, change the test, and it never fails for a real bug.
- Duplicate coverage: a new test whose failure mode an existing test already catches. Name the existing test.
- Tests of the framework or the library — a validation the framework guarantees, a getter, a constant.
- Setup-heavy tests for a trivial path, where the fixture costs more than the risk it covers.
- Flaky by construction: depends on the clock, on ordering, on network, on a sleep. It will cost reruns.

Gaps — the same read, inverted:
- Behavior this PR changed with no test touching it, where the untested path is the one that would actually break.
Report gaps as findings too, with `GAP` at the start of the title.

The bar for calling a test waste: state the regression the test would have to catch to be worth keeping, and why it cannot catch it. A slow or ugly test that would catch a real regression STAYS. Slow AND tautological is the finding.
```

### `{LENS_BRIEF}` — Product (`PROD`)

```
Read this diff as someone who has to USE the thing it delivers. Where does it fall over?

Hunt for:
- The intent says X — does the diff deliver X end to end, or only one layer of it? Model changed but not the serializer, permission or screen. Endpoint added that nothing calls. A setting the UI never exposes.
- States nobody handled: empty, none, one, many, too many. First run. Already done. Done twice at once. Permission denied. The record in a status the code assumes it is not in.
- Error paths: what the user actually sees when the call fails. A swallowed exception, a generic 500, a spinner that never resolves, a success message on a failed write.
- Other ways in: a background job, an API client, an import, another role that reaches this same code. Does the change hold for them?
- Data that already exists in production and the new code assumes it will not see — a null column, an old enum value, records created before this PR.
- No way back: a destructive migration, an irreversible state transition, a delete with no confirmation upstream.

The bar: name the user, the step, and what they see. "Could be a problem" is not a finding. If the hole is in a flow this PR did not touch, it is out of scope.
```

### `{LENS_BRIEF}` — Implementation (`IMPL`)

```
Read the changed code asking one question: is it correct? This is a careful read of the diff plus its immediate neighbours, not an audit.

Hunt for:
- The classics: null or undefined reaching something that dereferences it, off-by-one, an inverted condition, a mishandled early return, an unawaited async call, a swallowed exception, a loop variable captured by a closure.
- Contract drift: a signature, return shape or enum changed and a caller not updated. GREP THE CALLERS — this is the one exploration this lens must always do.
- Missing scope: a query without the tenant, user or company filter; a cache key missing a dimension; shared mutable state written from more than one path.
- Ordering and atomicity: two writes that should be one transaction, an external call inside a transaction, an event emitted before the commit that produced it.
- Performance that is visible at this project's real scale: a query inside a loop over a collection that grows with data, on a path called per request. Only when it will actually hurt here.

The bar: read the actual code at the location, not the diff hunk alone, and give the failing input or the sequence of steps in one sentence. Mark `Confidence: probable` when you can see the shape of the bug but could not confirm the path — that is honest and useful. Mark `unverified` and the finding will probably be cut, so only use it when the consequence is severe.

Not your job: style, naming, structure, type annotations, or how you would have written it.
```

## Phase 2 — the weighing (the orchestrator does this, no agent)

Every raw finding gets a verdict. This is the step that makes the review worth reading — a list of 14 true observations is not actionable, a list of 4 things worth doing is.

**Free pass — always `fix`, no argument needed.** A correctness bug in changed code with a named failing input, data loss, a security hole, a broken documented contract, a `GAP` on the exact behavior the PR exists to deliver.

**Everything else answers three questions:**

1. **What breaks if this is not done?** One sentence, concrete. No sentence means no gain.
2. **Is the gain observable?** A bug that stops happening, CI time that goes away, a caller that stops being wrong, a config that stops lying. Taste is not observable.
3. **What does it cost?** Diff size, blast radius, a flow that has to be re-tested, another review round, another day the PR stays open.

**Verdicts:**

| Verdict | When |
|---------|------|
| `fix` | Free pass, or the gain is concrete and clearly bigger than the cost |
| `call` | Real, but the gain is small or the cost is genuine. The author decides, and the row says which way it leans |
| `cut` | No named consequence, gain not observable, cost exceeds it, out of this PR's scope, or `unverified` with a non-severe consequence |

Three hard rules, so the weighing stays fast and honest:

- **Do not re-investigate.** A finding that arrives without a named consequence is `cut` for that reason. Reading the code again to rescue a badly written finding is exactly the cost this skill exists to avoid.
- **A `cut` is never deleted.** Every raw finding appears in the output. The author gets to disagree with the weighing, which they cannot do if they never see what was dropped.
- **Being right is not the same as being worth it.** A correct observation that buys nothing is a `cut`, and saying so is the job.

### The correctness read

One word for the header, from the Implementation and Product lenses only:

| Read | When |
|------|------|
| `broken` | At least one `fix` finding is a confirmed defect in the changed code, with a named failing input |
| `suspect` | A `probable` bug, or a `fix`-level product hole, but nothing confirmed broken |
| `holds` | No confirmed defect and no probable one |

`holds` means *nothing was found in one fast pass*. It does not mean the PR is good, and the output says so.

## Phase 3 — output (fixed shape, the orchestrator renders it)

This is the only thing the user sees. No raw agent output, no per-phase narration, no closing commentary.

**Header, two lines:**

```
## Quick Review — PR #123 — correctness: suspect — 4 fix / 2 call / 5 cut
14 files, +412/-89 — 4 lenses, 11 raw findings
```

**Table — `fix` and `call` rows only, `fix` first, then `call`:**

| # | Lens | V | Location | What is wrong | What to do | What it buys |
|---|------|---|----------|---------------|------------|--------------|
| 1 | IMPL | fix | `app/models/order.rb:88` | ... | ... | ... |

One line per cell, no line breaks inside a cell. `V` is `fix` or `call`. Location in backticks.

**Cut list — one line each, under `### Cut`:**

```
- TEST-3 — <finding in a handful of words> — cut: <reason in a handful of words>
```

**Closing line, verbatim, always:**

```
_One fast pass. `holds` means nothing was found, not that nothing is there — for depth, `/soffner:self-review`._
```

Zero findings across every lens: print the header, the closing line, and skip the table, the cut list and Phase 4.

## Phase 4 — the gate, and the end of the skill

The report lives in the message. It is **never written to a file**, and nothing in the repository is touched. The only thing this skill can write anywhere is a comment on the PR, and only after an explicit yes.

One question, last thing in the message, default no:

> Post the [N] `fix` findings as a comment on PR #[number]? (yes / no)

**On yes** — a single top-level comment, never inline comments. Inline placement is where a review call fails on a bad line number, and this skill is not the one to spend a retry loop on that; `/soffner:self-review` posts inline.

Pipe the body straight in, no file on disk:

```bash
gh pr comment <number> --body-file - <<'EOF'
## Quick Review — <N> achados
...
EOF
```

The comment body is written in **pt-BR**, on purpose — it is published on a PR whose audience is pt-BR, while this skill's own text stays English. Shape: a one-line header naming the origin, then one bullet per `fix` finding with location, what is wrong and what to do. `call` and `cut` rows are never published.

Report the comment URL in one line and stop.

**On no, or anything else** — stop. Nothing is written anywhere.

**The skill ends here, either way.** It does not fix a finding, not even the obvious one-liner, and it does not hand the findings to a skill that would. The fixing belongs to the session that wrote the code, in that session's own worktree, on its own triage. If the findings need to get there, the PR comment is how they travel — or the operator carries them over by hand.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Lenses launched one at a time | All of them in a single message, or the skill is not fast |
| A lens exploring the architecture to be thorough | Budget is the point, drop the finding instead |
| Orchestrator re-reading code to rescue a weak finding | `cut` it and move on |
| Publishing the whole table | Only `fix` rows are ever published |
| A bloat finding that is really a rewrite | The cost column says `large`, the verdict is `call` or `cut` |
| Every lens reporting 5 findings | Budgets are ceilings, not quotas. Zero is a valid lens result |
| Fixing a finding because it is only one line | This skill reports. The session that wrote the code edits |
| Writing the report to a file | The report is the message. The only write is the PR comment, after a yes |
| `holds` read as approval | The closing line stays, verbatim, every run |

## When NOT to use

- **Depth, or a project with real rules files.** `/soffner:self-review` — one reviewer per `.claude/rules/` file, a Panel that challenges findings and a Judge that settles them, published as inline comments.
- **Acting on the findings** — triaging them, deciding what is worth doing, editing the code. That is `/soffner:receiving-code-review`, run by the session that owns the work, never by this one.
- **Proving the thing actually works in a browser.** `/soffner:browser-test`.
- **No PR and no branch to diff.** There is nothing to read.
