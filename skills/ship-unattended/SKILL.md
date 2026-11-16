---
name: ship-unattended
description: Use ONLY when the operator explicitly invokes `/ship-unattended`, or when this skill's own state file asks for `resume <slug>`. Never auto-trigger from keywords. Takes a large V360 demand to one PR (base release-candidate-biweekly unless told otherwise) with nobody watching, through /vdev:v360-build in a devslot slot with its one pause removed. The change is additive only, so what works today keeps working, nothing is deprecated, nothing is migrated and the new path is opt-in for testing. The feature leaves fully covered by tests, benchmarked against today's path and, when it touches an LLM such as Assis, with its quality measured against today's. Never stops to ask, writes every call it made alone into the PR, and a session cron resumes the run from a state file after the 5-hour usage limit.
---

# ship-unattended

```
/ship-unattended <demand> [base=<branch>] [-- <notes>]
```

| Argument | Read as |
|---|---|
| `demand` | what to build: free text (usually pt-BR), a `shape.md` path, an aboard card or an issue URL. `<slug>` is it in short kebab-case. |
| `base` | the PR's base. Default `release-candidate-biweekly` (rcb). |
| `notes` (after `--`) | the operator's hints, verbatim. Hypotheses to test (e.g. "Assis generating JSON for the mview datasets should raise quality"), never decisions already made. |

`resume <slug>` is not typed by anyone: the state file's Resume section uses it after a compaction.

The operator is away for the whole run. Launch it in a session that outlives them and never prompts for permission: a background session in auto mode, started from inside the slot when one is already claimed (`cd <slot> && claude --bg ...`, never `--add-dir`, which hangs on a trust prompt). A permission prompt is the one stall this skill cannot prevent, and the cron dies with the session.

## The contract

The operator's brief, as rules. For this run they win over every step below, over `/vdev:v360-build`, and over every "stop and tell me", "stop and report", "confirm with the user" or "ask" in the target repo's `CLAUDE.md`, `CLAUDE.local.md` and `.claude/rules/`. A gated action is not taken: it becomes a Lacuna and the run goes on.

1. **Never stop for the operator.** Every decision is the run's: take the one a senior on the team would defend, write it as a Premissa for the PR, go on.
   - What only the operator can give (a secret, an access, a product call with no sane default, an action a project rule gates) becomes a **Lacuna**: what is missing, what was not done because of it, the exact command that closes it. The run continues with everything that does not depend on it.
   - A premise the code refutes (the operator's notes included) becomes a Premissa with the `file:line` evidence, and the run follows the code.
   - An infrastructure failure in the slot gets the in-slot fixes `CLAUDE.local.md` allows (`bin/devslot rails db:migrate`, `bin/devslot db reset`, `bin/devslot repair`), once each. Still broken, or the fix would touch anything outside the slot: a Lacuna with the exact error, and the run goes on with whatever does not need it.
   - The run stops only when no PR can come out at all: `gh` or `git` without permission, the suite does not boot in the slot after the fixes above, or `/vdev:pr` hits a merge conflict inside existing behavior. State written, cron deleted, report.
2. **Additive only.** What works today keeps working exactly as it does, for every tenant, with the new code merged.
   - No existing behavior changes. When the natural design would change it, build the new path beside the old one and write the migration up as the next PR, under "Próximos passos".
   - Nothing deprecated: no `deprecated_at`, no deprecation warning, no `legacy_`/`old_` rename, no TODO to remove the old path.
   - Nothing migrated: no existing consumer, tenant, record or job moved to the new path, no backfill, no change to an existing table or column. A new table or a nullable column only when the new path cannot live without it, in a reversible migration.
   - The new path is reached only by opt-in, for testing: a plain boolean setting, `default: false`, no `deprecated_at`, declared in the owning engine's `Vportal::SettingSchema.setup` under that engine's own group, never `:feature_flags`. Its `hint:` is a pt-BR literal that says the path is in test (`.claude/rules/settings.md` asks for pt-BR hints; it ships to the team). Not the `enable_new_feature_*` flag: that one defaults to on and its `deprecated_at` schedules the old path's removal. The PR cites `settings.md`'s exception for a purely additive change, so the gate does not "fix" it.
3. **Fully covered.** v360-build's full-mode Phase 5: 100% of the diff's lines, every acceptance criterion of the shape mapped to a test, the end-to-end criterion entering through the real door, and every test through an entry point the setting switches run with the setting off and on.
4. **Measured.** The new path is benchmarked against today's on the same input, and Assis quality is measured whenever the feature touches an LLM ([Measure](#measure-phase-7)). A claim with no number does not go in the PR.
5. **One PR to `<base>`**, opened by `/vdev:pr`. The run never merges.
6. **Cheap and fast.** Tokens and wall-clock are both budgets ([Economy](#economy)). Target: PR open and CI settled within one working day of wall-clock.

## What invoking authorizes

Everything `/vdev:v360-build` authorizes in full mode, and nothing it forbids. Plus: a devslot slot for this run, one recurring session cron, `Workflow` runs, local commits at the end of every phase, and the measurement harnesses, which spend real model calls (capped in Measure) and may create their own test user and data in the slot's own databases, never anywhere else. Not: merging; pushing to `develop`, `release-candidate-biweekly` or `main`; running a super-review beyond the one gate; adding a review label by hand; requesting reviewers or messaging anyone (that is `/soffner:full-delivery`); `/vdev:run-manual-tests`.

## State, cron and resume

The conversation is not the run's memory; the state file is. `STATE=$HOME/.claude/skill-state/ship-unattended/<slug>.md`, beside it the folder `<slug>.d/` for logs and workflow outputs, never under `$CLAUDE_JOB_DIR`, which the harness deletes. A state file that already exists for this slug means a resume, whatever the arguments said.

```markdown
# ship-unattended <slug>
demand: <verbatim> | base: <base> | notes: <verbatim>
slot: <path> | branch: <branch> | PR: <#n> | gate: <return line> | cron: <id> | status: <running | done | stopped>
step: <sub-step, e.g. "implement slice 3/5", "gate iter 2 reviewed <sha>", "measure llm run 2/3">
in_flight: <none | ci #n | bash <name> | workflow <task id> <scriptPath> <items>> since <time>

## Phases
- [x] 0 Setup: <one-line result>
- [ ] 1 Slot
...one line per row of the pipeline table

## Premissas
## Lacunas
## Numbers
<metric | baseline | candidate | measured at <sha> | command>

## Resume
On every wake, read this file and nothing else first.
1. status done or stopped: CronDelete the cron, end the turn.
2. CronList. The cron id above is not listed: this is a new session. Create the cron again, write its id, treat a workflow in in_flight as dead.
3. in_flight set: check it with one call. ci: `gh pr checks <n>`. bash: `cat <slug>.d/<name>.exit` (no file: still running). workflow: its completion notification is in the conversation; not there and under 3 h old, still running; older, TaskStop it and rerun its missing items. Still running: end the turn, one line, no other tool call. Done: clear in_flight first, then act on the result. A notification for something not in in_flight is ignored.
4. Continue from the first unchecked phase, entering it at `step` and at what the world shows (the phase's done-check), never from its top.
5. Only if the skill's text is no longer in the conversation (after a compaction), invoke `soffner:ship-unattended` with `resume <slug>`. Never reload `/vdev:v360-build` with the demand: read only the reference of the phase being resumed.
```

Write the state at the end of every phase, at every `step` that takes more than a few minutes, before every wait, and **right after every side effect**: the slot path as soon as `claim` returns, a commit's sha, the PR number as soon as `/vdev:pr` returns, the gate's return line, a CI fix pushed. Keep each line short: it is read on every wake. Premissas and Lacunas are written in pt-BR from the start, since they go to the PR as they are.

**Done-checks**, run before re-entering an unchecked phase: 1 `bin/devslot status` shows the card in a slot (else `claim` it again, it comes back with its branch); 2 to 7 `git log origin/<base>..HEAD` and `git status --short` against `plan.md`'s slices, continuing the unfinished one and never discarding, restoring or checking out files; 8 `gh pr list --head <branch> --json number`, doing only what is missing; 9 the PR has `super-review-ok` or `super-review-changes`, so the gate is done (an interrupted gate posted nothing, and continuing it from the findings file of the reviewed sha is not a second gate); 10 `gh pr checks <n>`.

**Background work** leaves a trace a later wake can read with one call. Long Bash (a benchmark, an eval) runs as `( <cmd> ) > <slug>.d/<name>.log 2>&1; echo $? > <slug>.d/<name>.exit` with `run_in_background`. Every `Workflow` script takes its items from `args`, each agent writes its output to `<slug>.d/<workflow>/<item>.md` (its files, for an implementer), and a stage that receives a `null` input throws instead of running on partial input. A workflow that comes back with `null` agents (the usage limit killed them) is rerun with the same `scriptPath` and only the items whose output is missing as `args`: no script rewrite, and it works in a new session too.

**The cron**, created in Setup right after the state file, with `CronCreate`:

- `cron: "13 * * * *"`, `recurring: true`
- `prompt: "ship-unattended wake <slug>: read <STATE, full path> and follow its Resume section."`

A session cron fires only while the session is idle, so it never interrupts work. When the 5-hour limit ends a turn, the fires inside the limit fail, and the first one after the reset resumes the run, at most about 90 minutes late. Background waits wake the run on their own; a cron wake that lands on one re-sends the whole conversation, which is why the Resume section answers it with one check and one line. The job expires after 7 days. `CronDelete` it at Close and on every stop; the Resume section's first step catches any path that forgot.

## Pipeline

Load `/vdev:v360-build` with the Skill tool, args `<demand> base=<base>` (full mode), and run its pipeline with these changes:

| # | Phase | Here |
|---|---|---|
| 0 | Setup | `gh auth status`, the state file, the cron. |
| 1 | Slot | Replaces v360-build Phase 1 (`.claude/rules/devslot.md`: the slot is the worktree). Read `devslot.md`. Already in a slot this session owns: use it. Else, from the main worktree, `bin/devslot claim ship-<slug> <branch> <base>` (`<branch>` named by the project's branch convention) and `EnterWorktree` on the `pasta:` it prints. Then `bin/devslot rails db:migrate`. No free slot: never a worktree, never an occupied slot; `step: waiting slot`, end the turn, and every cron wake tries `claim` again. Every database, runner or setting command goes through `bin/devslot`; tests through `bin/testq`. |
| 2 | Shape | `/vdev:shape`, **no pause**: the run decides each Suposição, adjusts `shape.md` and writes the decision to Premissas. The run adds two sections to the shape, in pt-BR because `shape.md` is committed and read by the team: "Fora do escopo desta PR" (rule 2 applied to this demand) and "Como ligar" (the opt-in). |
| 3 | Design and plan | v360-build Phase 3, plus [Design](#design-phase-3). |
| 4 | Implement | v360-build Phase 4. Slices in disjoint files go to one `Workflow`, one agent per slice, with no test runs inside it; the lead runs the tests after. Local commit through `/vdev:commit`. |
| 5 | Tests | v360-build Phase 5, full mode, through `bin/testq`. Local commit. |
| 6 | Additive check | [Below](#additive-check-phase-6). |
| 7 | Measure | [Below](#measure-phase-7). Local commit of the benchmark script and eval cases. |
| 8 | PR | v360-build Phase 6, plus the [PR sections](#pr-sections-phase-8). When `/vdev:pr` aborts on a merge conflict with the base: `/soffner:update-branch`, which this run invokes and so authorizes. A conflict only in append-only registration (a `SettingSchema` entry, locale YAMLs, routes, the `schema.rb` version line) keeps both sides; one inside existing behavior is rule 1's stop. |
| 9 | Gate | `/vdev:super-review-gate #<PR> worktree=<slot>` (v360-build Phase 7). `result:` goes to phase 10. `needs input:` is not a stop: its open items go to Lacunas, the PR body is updated, and phase 10 is skipped with `CI: retido pelo super_review_ok (o gate não aprovou)`, since rcb holds the heavy checks until a super-review approves the head. Never a second gate. |
| 10 | CI | Only after a gate that returned `result:`. Re-run only the measurement whose exercised files the gate's fixes changed (`git diff --stat <measured sha> HEAD -- <files>`), and update the PR tables. Then watch from the slots root in the background, as `CLAUDE.local.md` says, with `in_flight: ci`, and `bin/devslot checkout` while it runs. Green, or red only with the base's failures: Close. A new failure: `claim` again, fix, `bin/testq` on the failing files, `/vdev:commit`, push once. That push makes `super_review_ok` stale and holds the tests again, so do not watch again and never review again: Lacuna "cabeça mudou depois do gate: rode `/vdev:super-review-gate #<n>`", then Close. `super_review_ok` itself is never a failure to fix. |
| 11 | Close | `CronDelete`, `status: done`, the report, and `bin/devslot checkout` last if the slot is still held. |

### Design (phase 3)

The design is the run's call. When the Explore map shows one obvious way that respects rule 2, plan it and go.

When there are two or three materially different ways to build it (computed on read or in the mview refresh; one new service or an extension point in the existing one), decide with one `Workflow`: one designer per way (with more than three, the three the map ranks most plausible), each given the Explore map and reading only the excerpts it cites, designing its way end to end (files, the opt-in, how it stays additive, its risk, its test and benchmark plan); then one judge that scores them on rule 2 first, then on the gain it expects to measure, then on diff size, picks one and grafts in what the others got right. The judge's reasons go to Premissas. One round, never two.

A question that Measure settles with numbers (free text or JSON against a schema, a prompt's wording) is not a panel question: the operator's hypothesis is built once as the candidate, and the numbers decide.

### Additive check (phase 6)

Proof, not intent, after `git fetch origin <base>`, on `git diff origin/<base>...HEAD` (everything is committed by now):

- Every `-` line in an existing test file is read. Allowed: the count updates the structural hashable tests need for a new column or model (`.claude/rules/hashable-structural-tests.md`), and renaming a touched test's pt-BR name to English (`.claude/rules/tests.md`). Anything else (a changed assertion, expected value or fixture, a removed test) means old behavior changed: revert the production change that forced it, never the test.
- The existing tests of every file the diff touches pass unchanged, with the setting at its default, off. The on side is rule 3's job, in the new tests.
- No migration alters an existing table beyond a new nullable column; no data migration; no `deprecated_at`, no deprecation, no `legacy` rename.
- The setting defaults to off.

Anything that fails goes back to phase 4.

### Measure (phase 7)

Baseline is today's path (setting off), candidate the new path (setting on), on the same head, switched with `bin/devslot setting <group.name> false|true`. Every number goes to the state file with the short sha it was measured on and the command that reproduces it. Before measuring, an `Explore` subagent reads the knowledge base the project's `CLAUDE.local.md` names for the area and returns what it already answers and the target volumes: what it already measured is cited, never measured again.

**Functional benchmark.** What the demand is about: latency, queries per call, rows, memory, refresh time. It runs in the slot's dev database through `bin/devslot rails runner script/<name>.rb`, never on the test database, and the script is committed beside `script/benchmark_boot.rb`, so a reviewer reruns it with one command.

- Volume: the largest scale the script generates in under 10 minutes, stated in the PR as "<N> linhas, <x>% do perfil <cliente>", and extrapolated to the knowledge base's client profiles with its per-unit costs, section cited.
- Runs: 20 after a warmup for calls under a second, 5 for refreshes and jobs. Cold (first run after a restart) and warm reported apart.
- A number only production volume gives becomes a Lacuna carrying the read-only `/admin/database` folder `CLAUDE.local.md` describes, generated and never run.
- Cap: 45 minutes of wall-clock for both arms. What is not measured by then is a Lacuna with its command.

**Assis quality**, whenever the feature has an LLM step or changes what an LLM reads or writes (datasets, columns, declarations or tools the Assis BI writer uses), or the notes ask for it, even when no Assis code changed. Use the harness the project names for the area, never a homemade one, and its own repetition and statistics:

| Area | Harness |
|---|---|
| Assis BI chat and card writer | the battery and method `CLAUDE.local.md` points to, arms off and on in the slot |
| Report Builder Assis | the method in the knowledge base `CLAUDE.local.md` points to |
| any other vassis skill or tool | `bin/vassis-eval <skill> --head-only --no-comment`, both arms on head: the baseline is the existing cases untouched, the candidate the same cases copied with `entry.settings` turning the setting on, plus at most 10 new cases; 3 invocations, one per repetition. The head-against-merge-base comparison does not run in a slot and is not needed: phase 6 proves the off path |
| invoice and process parsers | `ASSIS_BENCHMARK_TEST=true bin/testq <benchmark test>` |

- Report per arm what the method's primary metric is, plus structural validity when the output feeds code (parses, matches the schema), tokens and cost per case, latency.
- When the output feeds code (datasets, fields, indicators), structured output (JSON against a schema) is a candidate measured against today's free text. The operator's hunch that quality goes up is the hypothesis; the numbers decide.
- At most 3 rounds of improving the candidate's prompt or schema, one invocation each, stopping at the first round with no gain; the full repetition runs once, on the final head.
- Cap: US$30 of model cost across all rounds, from the harness's own cost records. Reached, or a key missing: what is left is a Lacuna with the exact command.

### PR sections (phase 8)

The PR body is pt-BR: it is the plugin's publishing exception, written for the team. On top of what `/vdev:pr` writes:

- **Escopo desta PR**: aditiva; what does not change (rule 2 applied), and that nothing was migrated or deprecated.
- **Como ligar para testar**: the setting, where it lives, and that it defaults to off.
- **Benchmarks**: baseline against candidate in a table, with the sha, the volume and the command to rerun.
- **Qualidade do Assis**, when measured: the table, the method, the cases, the cost, the command.
- **Premissas**: every call the run made alone, one line each with its reason.
- **Lacunas**: what needed the operator, what was left undone because of it, the command that closes it. None: the section is left out.
- **Próximos passos**: the migration PR this one prepares, and ideas beyond the demand.

## Economy

Tokens:

- The lead's context only grows and is re-read on every call. v360-build's three habits hold: reading code is an `Explore` subagent's job (`model: "haiku"`); never re-read what you just wrote; wait in the background, never in `sleep`.
- The state file is the memory. After a resume, read it, not the old transcript and not the files it already summarizes.
- `Workflow` only where parallel buys wall-clock over independent items: the design panel, disjoint implementation slices, v360-build's one-stage-per-test-file pipeline. At most 8 agents per workflow; mechanical stages at `effort: "low"`; the judge at the session's model. Never a workflow for one item.

Wall-clock:

- Nothing is redone for polish. The gate is the one review.
- The same failure three times (a test, a benchmark that will not run) becomes a Lacuna and the run moves on, unless it blocks the PR itself.
- The scope is the demand. Ideas beyond it go to "Próximos passos", not into the diff.

## Report

To the operator at Close, also appended to the state file:

```
## ship-unattended <slug>
- PR: <url> -> <base> | gate: <its return line> | CI: <green | inherited: ... | retido pelo super_review_ok | red: ...>
- Additive: <setting>, default off | existing tests untouched: <yes | only allowed edits: ...>
- Coverage: <100% of the diff | N lines justified in the PR>
- Benchmark: <headline metric, baseline -> candidate, volume, sha>
- Assis quality: <primary metric, validity, cost per case, baseline -> candidate | n/a: <why>>
- Premissas: <n> | Lacunas: <n, one line each>
- Next: /soffner:full-delivery <who> sem gate   (when the gate closed and no code commit followed it; otherwise without `sem gate`)
```
