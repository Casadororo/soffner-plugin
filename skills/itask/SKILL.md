---
name: itask
description: Use ONLY when the user explicitly invokes `/itask`. Never auto-trigger from keywords or from a prompt that merely looks like the start of a task. Sanity-checks the opening prompt of a task by filling in worktree, base branch, new branch and next skill from the project's own conventions, then shows a compact table plus the goal and stops until the user confirms. It is pre-processing of the prompt, not an execution plan.
---

# itask

Reads the loose prompt that opens a task, fills in what was left implicit, and shows the interpretation back **before anything exists on disk**.

This is not a plan and not a design. It is the cheapest possible check on a misread prompt, run at the only moment where being wrong costs nothing. A base branch guessed wrong is discovered three files into the work, after a worktree was built and an environment set up on top of it.

## Flow

1. Parse the user's prompt.
2. Fill the missing fields from the defaults below.
3. Print the table, the goal and the question.
4. **Stop.** Execute nothing before the answer.
5. Corrected: adjust, reprint everything, ask again. Repeat until approved.
6. Approved: run the task as if the prompt had been the compact version.

## The fields

| Field | Default |
|-------|---------|
| Worktree | new |
| Base branch | the project's integration branch, in the order its `CLAUDE.md` documents; nothing documented means the repo's default branch (`gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`) |
| New branch | derived from the goal, kebab-case, following the project's branch convention when it documents one (a `branch` skill, a section in `CLAUDE.md`), including its area prefix |
| Next skill | resolved below |
| Goal | **required, no default** |

No goal in the prompt means ask for it and stop. Everything else can be guessed and corrected in one line; the goal cannot be guessed at all.

## Resolving the next skill

In order. First one that answers wins:

1. **The prompt names a skill.** "use /component-create" means that skill, no further thought.
2. **The prompt asks for design.** "brainstorm", "let's think about this first", "I don't know what I want yet" means `/soffner:brainstorming`.
3. **The project ships a shaping skill.** A `shape` skill — the one that writes a functional spec before the code — is the default. This is the normal path.
4. **It does not.** Then **implement directly**. No plan document, no spec, no substitute step.

Case 4 is a decision, not a gap. A project without a shaping step does not get a generic planning skill wheeled in to fill the space — the work starts. Write `implement directly` in the table so it is visible and can be overridden in one word, the same as any other field.

Check what is actually invocable in **this** session, by reading the session's skill list, not by assuming a skill exists because the project had one last month.

## Output, exactly this shape

```
| Worktree | Base | Branch | Next skill |
|----------|------|--------|------------|
| <new or path> | <base> | <branch> | <skill or "implement directly"> |

Goal: <one line>

Can I go ahead?
```

Then stop. Nothing runs before the answer — no worktree, no branch, no fetch.

## Examples

**Prompt with everything spelled out:**

```
work in a new worktree, branch bi/v0/card-filters off origin/bi/v0/cache,
brainstorm it first, goal: per-card filters (month/day granularity switch,
generic UI). Check whether the mview filters can be reused.
```

```
| Worktree | Base | Branch | Next skill |
|----------|------|--------|------------|
| new | origin/bi/v0/cache | bi/v0/card-filters | /soffner:brainstorming |

Goal: per-card filters (month/day granularity switch, generic UI; check reuse of the mview filters)

Can I go ahead?
```

**Minimum prompt, project with a `shape` skill:**

```
/itask add an audit log to the exports
```

```
| Worktree | Base | Branch | Next skill |
|----------|------|--------|------------|
| new | origin/release-candidate-biweekly | audit-log-exports | /shape |

Goal: add an audit log to the exports

Can I go ahead?
```

**Same prompt, project without one:**

```
| Worktree | Base | Branch | Next skill |
|----------|------|--------|------------|
| new | origin/main | audit-log-exports | implement directly |

Goal: add an audit log to the exports

Can I go ahead?
```

## Correction

"wrong branch, use X", "base is develop", "no, shape it first" — adjust that field, reprint the **whole** table plus the goal plus the question, and wait again.

Reprint everything, never just the corrected line. The point of the table is that the user reads four fields at once; a correction that shows only the delta forces them to rebuild the rest from memory, which is where the second misread comes from.

## After approval

Execute as if the original prompt had been:

> worktree `<X>`, base branch `<Y>`, new branch `<Z>`, using `<S>`, for goal `<G>`

Typically:

1. **Worktree**, when the answer was `new`. Through the project's worktree flow if it ships one (a `worktree-setup` skill or equivalent), since that is what also performs the environment setup — dependencies, gitignored files, fixtures, assets. No such flow means `git worktree add` plus whatever setup the project documents.
2. **Next skill**, with the goal as its context. Or, when the field says `implement directly`, start the work.

The approval covers the four fields and the goal. It is not approval to commit or to push, which stay where they are everywhere else in this plugin — only on an explicit request.

## When NOT to use

- **The task needs no worktree or branch.** Reading, a quick debug, a local config tweak.
- **Already on the right branch**, just running the next step.
- **Editing `CLAUDE.local.md`, `settings.local.json` and the like.**
- **Taking over an existing PR.** The branch and the base are already decided — that is `/soffner:dono`.
