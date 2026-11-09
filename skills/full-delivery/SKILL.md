---
name: full-delivery
description: Use ONLY when the operator explicitly invokes `/full-delivery`. Never auto-trigger from keywords. Takes the PR this session is working on all the way to a reviewer by running /vdev:super-review-gate, then /vdev:run-manual-tests, then /soffner:deliver, one after the other, each only after the previous one came back clean, and stops at the first that does not. Reads the free text after the command for who receives the PR and which steps to skip.
---

# full-delivery

```
/full-delivery <free text>
```

Three skills in a row, on **the PR of this conversation**:

1. `/vdev:super-review-gate`
2. `/vdev:run-manual-tests`
3. `/soffner:deliver`

A step starts only when the previous one finished **and came back clean**. Anything else stops the run there, and the steps after it do not run.

Invoking authorizes everything the three skills do on their own (commit and push on the PR branch, the test environment, the Slack message). No confirmation between steps.

## 1. Read the request

The text after `/full-delivery` is free, usually pt-BR. Read it for:

- **Who receives it.** One or more people, passed as they are to `deliver` (which sends each one their own DM).
- **Steps to skip.** "sem manual test", "sem teste", "pula o teste" skips step 2. "sem review", "sem gate" skips step 1. "sem deliver", "não manda" skips step 3.
- **Gate mode.** "supercritico" → `modo=supercritico`. Default `modo=normal`.
- **A note for the message.** Text after `--`, or anything clearly meant for the reviewer, goes to `deliver` as its `-- note`.

| Request | Runs |
|---|---|
| `nathan` | gate → tests → deliver to Nathan |
| `nathan sem manual test` | gate → deliver to Nathan |
| `nathan e joão supercritico` | gate (supercritico) → tests → deliver to Nathan and João |
| `nathan -- a do aboard vai primeiro` | gate → tests → deliver to Nathan, with the note |

No person named and deliver not skipped: ask who before starting anything, never after the gate and the tests already ran. Text you cannot place: ask before starting, with your reading as the first option.

## 2. Resolve the PR

Once, at the start, the way `deliver` does it: the PR named or opened in this conversation, else `gh pr view --json number,url` on the current branch. Never pick from a list of open PRs. No PR: ask. Every step gets this same number.

## 3. Run

Invoke each skill with the Skill tool and read its final lines to decide.

| Step | Invocation | Clean when | Stops on |
|---|---|---|---|
| 1 | `vdev:super-review-gate` `#<PR> modo=<m>`, plus `worktree=<path>` when this session is in the PR's worktree | the return line starts with `result:` (gate fechado) | `needs input:` or `failed:` |
| 2 | `vdev:run-manual-tests` `<PR>` | the checker's last line is `RODADA: LIMPA` | `RODADA: NAO LIMPA`, `failed:`, or no `RODADA:` line |
| 3 | `soffner:deliver` `<people> [-- note]` | the review request went out | (last step) |

Never fix a step's findings yourself to push it to clean, and never re-run it hoping for another result. A stop is the operator's call.

## 4. Report

One line per step: passed (with the gate's verdict comment or the test report link), skipped (because the request said so), stopped (with the line that stopped it), or not run (an earlier step stopped). When deliver ran, its own report closes: the PR URL, the reviewers, and one Slack permalink per person.
