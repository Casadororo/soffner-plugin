---
name: level-up
description: Use ONLY when the user explicitly invokes `/level-up`, or when a launch prompt starts with it. Never auto-trigger from words like improve, polish or upgrade. Runs one autonomous session that takes a scope (a PR, a part of the product, or the whole product in the current repository) and an optional ambition, and returns it much more valuable in one PR - a spec built by walking every persona's journey, a written bar that today's product fails, building rounds, and an independent evaluator with no build history that grades the running product after each round. It stops on the bar, not on an open PR. Asks nothing.
---

# level-up

```
/level-up <scope> [-- <ambition>]
```

| Scope | Read as | The run's PR |
|-------|---------|--------------|
| `123`, `#123` or a PR URL | what that PR delivers, its description included, judged as a product and not as a diff | that PR: its branch, updated in place |
| an area: a feature, flow, screen, path or module, named the way the team names it | that part of the product and every journey that crosses it | a new one |
| absent, or `product` | the whole product in the current repository | a new one, unless the ambition names an existing PR to start from |

`<ambition>` is optional free text after `--`: who it is for, what has to be true when the run ends, what is fixed. Without it, the ambition is to make the scope much more valuable to the people who use it, and the bar decides what that means.

**The scope bounds the bets, not the journeys.** Journeys are walked end to end even when they start outside the scope, because a part is only as good as the path into it. The changes stay inside the scope, plus whatever a bet cannot land without; each change outside the scope is named in `spec.md` with the bet that needs it.

Launch it as its own background session, from the repository (or dev slot) folder, with the highest effort the launcher allows:

```bash
claude --bg --effort max -n "<Product> - level-up" "/soffner:level-up <scope> -- <ambition>"
```

## What the invocation authorizes

Deciding alone, without asking anyone. Committing and pushing on the run's branch as often as the work needs, and opening and updating its PR. Running the product locally, its tests, its CI script, a browser against it, and database writes on the local development database (or the slot's, when the folder is a dev slot), including the test users the run needs. Outside it: merging, pushing to a shared branch, anything that touches production or another person's environment.

## Nobody is watching

- **Never ask, never wait, never ping.** No questions, no "should I", no message to anyone (Slack, board cards, mentions). The PR and `progress.md` are the only places this run writes for people.
- **Ambiguity is not a reason to stop.** Pick the option that serves the ambition best, write it under "Premises" in `progress.md`, and carry on.
- **A blocked action is a detour, not a wait.** A command that needs someone's approval stalls the session until a person shows up. Prefer the project's documented commands; when an action is refused or blocked, take another path and record it in `progress.md` instead of retrying it.
- **Stop early only when the environment is broken and you cannot repair it** (the product will not boot, CI infrastructure is down): record the exact error in `progress.md` and in the PR, and end.

## One PR

Everything the run produces lands in **one** PR, the one the scope table names: the scope's own PR, or an existing PR the ambition names as the starting point, worked on its branch and updated in place; otherwise one new branch, by the project's naming convention, and one new PR. No second PR, no follow-up PRs, no side PR for something found on the way: it goes in this one, or in its list of what is left.

## Ground rules

- **The bar is the finish line.** A PR is a delivery container, opened early as a draft and updated every round. It never means done.
- **The repository's rules bind the code, not the product.** `CLAUDE.md`, `AGENTS.md` and the project's rules govern how code is written, tested and committed: follow them. The screens, flows and domain model that exist today are evidence of where the product is, not a constraint on where it goes, unless the ambition says something is fixed.
- **Value, not decoration.** A change earns its place by what a persona can now do, or do faster, that they could not before. Visual work counts when it makes a journey clearer or shorter, never on its own.
- **Never weaken the bar to pass it.** Do not delete, loosen or rewrite a criterion, and do not remove or edit tests to make them pass. A criterion that turns out to be wrong gets replaced by a stricter or equally strict one, with the reason in `progress.md`.
- **Read the environment first.** The repository's `CLAUDE.md` and `AGENTS.md`; when the main worktree has `.claude/rules/devslot.md` and this folder is a slot, that rule too (database, port, host).
- **Be on the run's branch.** When the run's PR already exists and the folder is on another branch, `gh pr checkout <pr>` with a clean tree; a dirty tree on the wrong branch is a broken environment.

## The run directory

Everything that has to survive a compaction lives on disk, in `.level-up/` at the worktree root. Add `/.level-up/` to `$(git rev-parse --git-common-dir)/info/exclude` so it never reaches a commit.

| File | Holds | Written by |
|---|---|---|
| `spec.md` | personas, the job each one has, end-to-end journeys, the bets and the cross-cutting decisions | lead, phase 2 |
| `bar.json` | the criteria, each with a threshold and how to verify it | lead, reviewed by an evaluator, phase 3 |
| `progress.md` | premises, round log, scores per round, refine/pivot decisions, what is next | lead, after every step |
| `evals/round-N/<evaluator>.json` | one evaluator's verdicts and evidence | lead, from the evaluator's result |
| `evals/round-N/shots/` | screenshots the verdicts point to | evaluators |

After any compaction, and at the start of every round, reread `spec.md`, `bar.json`, the tail of `progress.md` and `git log --oneline -20` before doing anything else.

`bar.json` is JSON on purpose: a model rewrites prose freely and structured data much less.

```json
{
  "criteria": [
    {
      "id": "J2-handoff-without-slack",
      "journey": "J2",
      "persona": "portal developer",
      "claim": "Starting cold, the developer gets everything needed to implement screen X from the product alone, without asking anyone",
      "verify": "Sign in as the developer, start from the home page, implement-ready means: spec, states, tokens, assets and the copy-paste prompt for the portal agent",
      "threshold": 1.0,
      "kind": "journey"
    }
  ]
}
```

Kinds, and their default threshold: `journey` (a persona finishes a job end to end, 1.0), `depth` (the interactions are real, not display-only, 0.8), `quality` (correctness, performance, CI green, 1.0), `edge` (empty, error, permission and narrow-screen states, 0.8).

## Phase 1: walk today's product

Before changing anything, find out where the product stands, in parallel:

- **One browser worker per persona** (below) walks that persona's main jobs in the running product, from a cold start, and reports where each journey breaks, stalls, or sends the person elsewhere (Slack, a spreadsheet, another tool).
- **One subagent reads the code and the domain model** and reports what the model makes easy, hard or impossible.
- **One subagent studies what the best products in the space do** for the same jobs, to find where this product can win for its own users, not to copy.

Each one gets an objective, the output format (a short report with evidence: steps, screenshot paths, `file:line`), the tools to use, and what it must not do (no code changes). Each returns a condensed report, not its whole trace. Write their findings into `progress.md`.

### Browser workers

Anything that drives the product in a browser runs as its own `claude -p` process with an isolated headless browser, never as a subagent: subagents share this session's one browser, and parallel ones overwrite each other's pages. Boot the product once (the slot's server in a dev slot), then start one worker per slice in the background:

```bash
claude -p "$(cat .level-up/<worker>.prompt.md)" --model <strongest available> --output-format json \
  --mcp-config "<SKILL_DIR>/../browser-test-auto/playwright-mcp.json" --allowedTools mcp__playwright \
  > .level-up/<worker>.out.json 2> .level-up/<worker>.err
```

`<SKILL_DIR>` is the base directory shown when this skill was loaded. The worker's report is the `.result` of its output file. Screenshots take an absolute `filename`; a relative one lands in the process's working directory, where workers overwrite each other. When the product has accounts, create one user per worker in the local database with the role its persona has, and hand the worker its credentials: one sign-in must not end another's session, and the operator's account is never used. A product without a UI gets the tools it is driven by instead (`--allowedTools "Bash(<its cli>:*)"`).

## Phase 2: the spec

Write `spec.md` from the reports and the ambition. Be ambitious about scope and stay at the level of the product: personas, jobs, journeys, the domain model, the high-level technical design. No implementation steps.

- **Bets.** Each bet names who gains and what changes in that person's day. Rank them by that. Distrust the obvious (a dashboard, better search, dark mode) unless you have an angle nobody else has.
- **Cross-cutting decisions are made here, once.** The domain model, the product's visual language, naming, how the main objects relate. Parallel builders later inherit these decisions instead of making conflicting ones of their own.

## Phase 3: the bar

Write `bar.json`: criteria per journey, plus `depth`, `quality` and `edge` criteria, each one checkable by an outsider using the running product.

1. **An evaluator reviews the bar before you build** (the template below, in contract mode). It flags criteria that are vague, unverifiable or too easy, and missing journeys. Revise until it has no objection left.
2. **The bar has to fail today.** Run one full evaluation round on the untouched product (round 0). If it passes more than a few criteria, the bar is describing today's product, not the ambition: raise it and run round 0 again.

## Phase 4: build rounds

Each round:

1. **Pick the work** with the largest gain: failing `journey` criteria first, then the bets they depend on.
2. **Build.** One builder by default: coding is mostly sequential, and parallel writers make conflicting implicit decisions. Run builders in parallel only on areas that share no files and no open design question, each with its own verification. Commit after every coherent step so a bad turn can be rolled back. Keep the project's tests and CI green as you go, not at the end.
3. **Check your own work before the evaluator does**: boot the product and walk the journeys you touched. This catches crashes; it does not count as evaluation.
4. **Evaluate** (below), then **decide** (below).
5. **Update `progress.md`** (round, what changed, scores, decision) and push. Update the draft PR.

## Evaluation

Every round runs fresh evaluators: new browser workers with no build history. Run one per journey, or one per persona when journeys are short, in parallel. Use the strongest model available for them: judging is the step the result depends on.

An evaluator gets only: `spec.md`, `bar.json`, how to run and sign in to the product, and its slice of criteria. Never the diff, the build log or your opinion of the work.

```
You are a demanding <persona> trying to get <job> done with this product, and a skeptical QA
engineer. You did not build it and you owe it nothing. Agents judging generated work tend to
praise it; correct for that.

Run the product (<how to run, URL, sign-in>) and use it the way <persona> would, from a cold
start. Read code only to explain a failure you already saw in the product, never to award a pass.

For each criterion in <criteria ids> from <path to bar.json>:
- Do what "verify" says. Record the steps you took and save a screenshot to <shots dir>.
- Score 0.0 to 1.0 and give pass or fail against the threshold. When unsure, fail.
- A feature that exists but the persona cannot find unaided counts as missing.
- A feature that only displays, where the job needs interaction, scores at most 0.3.

Then list the complaints that would stop <persona> from choosing this product over what they
use today, most damaging first. Report anything broken you saw outside your criteria.

End with only this JSON: {criteria: [{id, score, pass, steps, evidence, why}], complaints:
[...], other_bugs: [...]}. Change nothing in the product or the repository.
```

Save each worker's `.result` to `evals/round-N/<evaluator>.json`.

In **contract mode** (phase 3), the evaluator is a plain subagent with no browser: it reads `spec.md` and `bar.json` and returns the criteria it would reject, and why.

**The lead may take trust away, never give it.** Reject a pass you cannot reproduce. Never turn a fail into a pass, and never settle a criterion from what you know about the code. A disputed fail goes to the next round's evaluator, which sees the product as it is then.

## Decide after each round

- **Refine** when the failing scores are rising: next round on what still fails.
- **Pivot** when a bet has not moved after two rounds: the approach is wrong, not the effort. Rework it from the spec down (sometimes a different domain model, sometimes a different screen structure) and record the pivot and the reason in `progress.md`.
- **New complaints count.** A complaint that would stop a persona from choosing the product becomes a criterion in `bar.json`, held to the same rules as the rest.

## When to stop

Only when a fresh evaluation round passes every criterion at its threshold, reports no complaint that would stop a persona from choosing the product, and the PR's checks on the remote are green (`gh pr checks <pr> --watch`; a failure the base branch already has is recorded, a new one is fixed). Nothing else ends the run: not an open PR, not green CI alone, not a feature list that looks complete.

The one other exit is a plateau: two consecutive rounds with no score gain on the remaining failures, after a pivot was already tried on them. Then stop, and the PR states plainly what is still below the bar and why.

## The delivery

The run's one PR, updated to its final state and marked ready for review (`gh pr ready`), unless the run stopped on a broken environment. Its title and body go to the team, so they follow the project's language (pt-BR for V360, the plugin's publish exception). The screenshots reach the body through `gh pr edit <pr> --body-file <body.md> --attach <png>...`: a body that references a local file (`![alt](./shot.png)`) gets that reference swapped for the uploaded URL. Read the body back afterwards; a non-zero exit can still have uploaded some of the files. The body covers:

- what the product does now, journey by journey, before and after, with screenshots from the evaluators' evidence;
- the bar, with the round-0 scores next to the final scores;
- the bets that made it, the ones that were cut and why, and the pivots;
- the premises taken without asking;
- what is still below the bar, if the run ended on a plateau.

Then print, to the operator in English, the PR link, the final scores, and the path of `.level-up/`.
