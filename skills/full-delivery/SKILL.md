---
name: full-delivery
description: Use ONLY when the operator explicitly invokes `/full-delivery`. Never auto-trigger from keywords. Takes the PR this session is working on all the way to a reviewer by running /vdev:run-manual-tests, then /vdev:super-review-gate, then the repo's own pr-classify (skipped when the repo has none), then /soffner:deliver, one after the other, each only after the previous one came back clean. A bug a step finds is fixed and the step runs again; the run stops only on a design or architecture problem, or a step that could not run. Reads the free text after the command for who receives the PR and which steps to skip.
---

# full-delivery

```
/full-delivery <free text>
```

Four skills in a row, on **the PR of this conversation**:

1. `/vdev:run-manual-tests`
2. `/vdev:super-review-gate`
3. `pr-classify`, a skill local to the PR's repository. Not found there: skip it and go to step 4.
4. `/soffner:deliver`

A step starts only when the previous one finished **and came back clean**. A step that found a bug gets it fixed and runs again ([Fix and go on](#fix-and-go-on)). Only a design or architecture problem, or a step that could not run, stops the run there, and the steps after it do not run.

Invoking authorizes everything the four skills do on their own, plus the bug fixes below (commit and push on the PR branch, the test environment, the `ai-merge` label and its comment, the Slack message). No confirmation between steps.

## 1. Read the request

The text after `/full-delivery` is free, usually pt-BR. Read it for:

- **Who receives it.** One or more people, passed as they are to `deliver` (which sends each one their own DM).
- **Steps to skip.** "sem manual test", "sem teste", "pula o teste" skips step 1. "sem review", "sem gate" skips step 2. "sem classify" skips step 3. "sem deliver", "não manda" skips step 4.
- **Gate mode.** "supercritico" → `modo=supercritico`. Default `modo=normal`.
- **A note for the message.** Text after `--`, or anything clearly meant for the reviewer, goes to `deliver` as its `-- note`.

| Request | Runs |
|---|---|
| `nathan` | tests → gate → classify → deliver to Nathan |
| `nathan sem manual test` | gate → classify → deliver to Nathan |
| `nathan e joão supercritico` | tests → gate (supercritico) → classify → deliver to Nathan and João |
| `nathan -- a do aboard vai primeiro` | tests → gate → classify → deliver to Nathan, with the note |

No person named and deliver not skipped: ask who before starting anything, never after the tests and the gate already ran. Text you cannot place: ask before starting, with your reading as the first option.

## 2. Resolve the PR

Once, at the start, the way `deliver` does it: the PR named or opened in this conversation, else `gh pr view --json number,url` on the current branch. Never pick from a list of open PRs. No PR: ask. Every step gets this same number.

## 3. Run

Invoke steps 1, 2 and 4 with the Skill tool, and read each step's final lines to decide.

| Step | Invocation | Clean when | Not clean on |
|---|---|---|---|
| 1 | `vdev:run-manual-tests` `<PR>` | the checker's last line is `RODADA: LIMPA` | `RODADA: NAO LIMPA`, `failed:`, or no `RODADA:` line |
| 2 | `vdev:super-review-gate` `#<PR> modo=<m>`, plus `worktree=<path>` when this session is in the PR's worktree | the return line starts with `result:` (gate fechado) | `needs input:` or `failed:` |
| 3 | `pr-classify` `#<PR>` (see below) | the return line starts with `result:`, whatever the verdict | `failed:`, or no `result:` line |
| 4 | `soffner:deliver` `<people> [-- note]` | the review request went out | (last step) |

**Finding `pr-classify`.** It lives in the PR's repository, not in a plugin. Look, in this order, for a skill named `pr-classify` in the Skill tool's list, then for `.claude/skills/pr-classify/SKILL.md` and `.claude/skills-lib/pr-classify/SKILL.md` at the root of the PR's worktree (`git rev-parse --show-toplevel`). A `SKILL.md` outside the Skill tool's list is run by reading it and following it with `#<PR>` as the argument. None of them: the step is skipped (not stopped) and the run goes on to deliver.

**A `não` from `pr-classify` is not a stop.** It only means the PR does not get the `ai-merge` label, so a human reviews it, which is what deliver asks for. Carry the verdict and its reasons to the report.

### Fix and go on

A step that is not clean because of what it found in the PR is fixed here, not handed back:

- **Bug: fix it and run the step again.** Anything wrong inside what the PR already set out to do: a manual-test item that failed, a crash, a wrong value or state, a broken screen, a missing permission check or translation, a gate item left open that fits in the PR's scope. Minimal fix with a regression test at the lowest level that reproduces it (`.claude/rules/tests.md`), only the touched tests run (`bin/testq` in a devslot slot), commit through `/vdev:commit`, push. Then the same step again: `run-manual-tests` as its retest of the fix (the fix's shas in the prompt; its retest procedure decides what to redo), the gate as a new `super-review-gate` run. Clean: go on to the next step.
- **Design or architecture: stop.** Fixing it changes the PR's approach: the data model or a migration, a contract other code relies on, the screen's layout or flow as designed, a product rule nobody wrote down. That is the operator's call. Findings that mix both stop too, with each one labeled bug or design in the report.
- **The step could not run** (`failed:` with no finding: no environment, no PR): stop.

The same step still not clean after 3 fix rounds: stop, with what is still open. Never re-run a step without a fix in between, hoping for another result.

## 4. Report

One line per step: passed (with the test report link, the gate's verdict comment, or the classify verdict, `ai-merge` or `não` with its reasons, and the bugs fixed on the way with their commits), skipped (because the request said so, or `pr-classify` is not in this repo), stopped (with the line that stopped it), or not run (an earlier step stopped). When deliver ran, its own report closes: the PR URL, the reviewers, and one Slack permalink per person.
