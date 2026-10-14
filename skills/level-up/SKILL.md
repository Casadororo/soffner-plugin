---
name: level-up
description: Use ONLY when the user explicitly invokes `/level-up`. Never auto-trigger from words like improve, polish or upgrade. Takes a scope (a PR, a part of the product, or the whole product in the current repository) and improves it in one PR, unattended - one short triage that lists only improvements backed by evidence, then at most three stages of direct code changes, each tested and committed. Little to improve means a small, fast PR, or none. It never invents work, never loops, and asks nothing.
---

# level-up

```
/level-up <scope> [-- <ambition>]
```

| Scope | Read as | The run's PR |
|-------|---------|--------------|
| `123`, `#123` or a PR URL | what that PR delivers, description included | that PR, on its branch |
| an area: a feature, flow, screen, path or module | that part of the product | a new one |
| absent, or `product` | the whole product | a new one, unless the ambition names a PR to start from |

`<ambition>` is optional free text after `--`. It decides what counts as gain when ranking; it never adds work that has no evidence behind it.

**The run is measured by what lands in code, and it always ends.** Reading is capped, the number of stages is fixed before the first edit, and an item that grows past its size is dropped, not chased.

## Ground rules

- **Nobody is watching.** Never ask, never wait, never message anyone. Ambiguity: pick the leaner option and note it as a premise in the PR.
- **One PR**, the one the table names. No side PRs; what is left goes in its list of next steps.
- **One session, subagents only.** Never start another session (`claude -p`, `claude --bg`, or a skill that does). Subagents never start subagents. Use them only to read disjoint areas at once during triage, or to edit disjoint files at once in a stage.
- **Nothing that is not the product.** No spec, rubric, persona document, research report or review rounds. The one file kept outside the code is `.level-up/plan.md`, added to `$(git rev-parse --git-common-dir)/info/exclude`, so a compaction does not lose the plan.
- **The repository's rules bind the code:** `CLAUDE.md`, `AGENTS.md`, and the devslot rule when this folder is a slot. When the run's PR exists and the folder is on another branch, `gh pr checkout <pr>` with a clean tree.

## 1. Triage: one pass

Read the scope once: for a PR, its description and diff; for an area or the product, its code paths, its tests, recent `git log`, `TODO`/`FIXME`, and the open issues that mention it. Run its tests. With a UI, go through the main flow once.

Write `.level-up/plan.md`, one line per improvement:

- **evidence:** something that exists now. `file:line`, a failing or missing test on real logic, a step that is broken or confusing when you use it, a `TODO`, an error in the logs;
- **gain:** what a user or a maintainer gets, in one sentence;
- **size:** S (a few edits), M (an afternoon of edits), L (more).

No evidence, no item. "Could be nicer", a feature nobody's work points to, and changes of taste stay out: that is inventing work. Rank by gain over size. Triage ends here; it does not branch into research.

## 2. Size the run

| The list | The run |
|----------|---------|
| empty | No PR. Report "nothing worth changing" and what was checked. Done. |
| up to ~6 items, mostly S and M | One stage with all of them. |
| longer | Up to 3 stages, each a coherent group (one area or one root cause), highest gain first. Everything after the third stage goes in the PR as next steps and is not done in this run. |

Write the stages into `plan.md` before the first edit. The count never grows during the run.

## 3. Each stage

1. Edit the code. Fix root causes, delete before adding, follow the project's conventions.
2. Run the tests that cover the change; add a test only for real logic. A UI change: look at the changed screen once (a headless screenshot through `<SKILL_DIR>/../demo/demo-take.js rehearse` works, inside a slot on the slot's host). `<SKILL_DIR>` is the base directory shown when this skill was loaded.
3. Commit, push, mark the items done in `plan.md`.
4. An item bigger than its size, or blocked: stop it, list it in the PR as not done with the reason, move on.

The tests and the look in step 2 are the verification. No review rounds and no evaluators.

## 4. Deliver

1. The project's CI script, or the tests the change touches, green locally. Then `gh pr checks <pr> --watch` once: a new failure gets at most two fix attempts; a failure the base already has is noted.
2. The PR body, in the project's language (pt-BR for V360, the plugin's publish exception): each item done, with its evidence and what changed; what was left, ranked, with sizes; the premises taken.
3. Mark it ready for review (`gh pr ready`) and print to the operator the PR link and the count of items done and left.
