---
name: brainstorming
description: Use ONLY when the user explicitly invokes `/brainstorming`. Never auto-trigger from keywords, and never enter it because a request looks like a feature. Turns an idea into a design by reading the repo first, carrying what is left over as explicit assumptions, and spending the user's attention in batches instead of one question per message. A rejected assumption rewinds the work to the last accepted checkpoint.
---

# brainstorming

Turns an idea into a design that is ready to implement.

What makes this version different from the usual brainstorming loop is where it spends. It does **not** ask one question per message and it does **not** stop after every step. It reads the repository to answer everything the repository can answer, carries the rest forward as **explicit assumptions**, and interrupts the user in **batches**, only at the points where being wrong is expensive.

## The trade

Tokens are cheap. The user's attention is not.

Prefer reading ten files over asking one question. Every question the code could have answered is a defect in how this skill was run — going and looking costs a tool call, asking costs a context switch and a wait.

This cuts both ways: exploring more is the price of gating less. A batch of assumptions built on a repo you did not read is not a shortcut, it is a guess with better formatting.

## The ledger

The whole mechanic sits on one table, kept up to date in chat:

```
| # | Decision | State | Rests on |
|---|----------|-------|----------|
| 1 | Auth goes through the existing session middleware | ACCEPTED | — |
| 2 | New rows live in `invoices`, no new table | ASSUMED | 1 |
| 3 | The job runs inline, no queue | ASSUMED | 2 |
```

- **ACCEPTED** — the user said yes to it, explicitly. Only the user moves an entry into this state. Silence is not acceptance.
- **ASSUMED** — you chose it in order to keep moving. It is real work in progress, not a placeholder, and you build on it as if it were true.
- **Rests on** — which earlier entries this one depends on. Fill it in as you go, because it is what makes rollback mechanical instead of a judgement call later.

Every artifact you produce — a design section, an explored path, a file — records which entries it rests on.

Nothing ever rewinds past an ACCEPTED entry.

## When to open a gate

Open one when any of these is true:

- **Three or four assumptions are open.** Past that, one wrong answer takes too much with it.
- **The next step is expensive or hard to undo.** Writing production code, creating files, touching shared state, anything that costs more to unwind than to ask about.
- **A single assumption is load-bearing.** One entry that half the design rests on gets its own gate, even if it is the only one open.

The test is always the same: **if this assumption is wrong, what do I throw away?** Less than a message's worth means keep going. More than a few minutes of real work means gate now.

Do **not** open a gate:

- To confirm something the repo already answers. Go read it.
- To announce progress, or to ask whether to continue.
- After each design section, one section at a time.
- Because the step felt big. Size is not the trigger — rollback cost is.

## The gate itself

One `AskUserQuestion` call, up to four questions, one per open assumption. Each question carries the real alternatives you weighed, your pick first and marked as recommended, and enough of the consequence for the user to choose without reading the repo themselves.

Around the call:

- **Before it**, print the ledger, so the user sees what they are confirming and what rests on it.
- **After it**, print the updated ledger with the new states, including any rollback the answers triggered.

An assumption that is not worth a question is not an assumption, it is a decision — state it in the ledger as ACCEPTED-BY-DEFAULT and move on. Do not burn one of the four slots on it.

## Rollback

An answer that rejects an assumption is the normal case, not a failure. It is the reason working on assumptions is safe.

When entry **N** is rejected:

1. Name it out loud, with the correction the user gave.
2. Collect everything that rests on N, directly or transitively, through the `Rests on` column.
3. **Discard all of it.** Design sections, explored branches, files already written. Say explicitly what is being thrown away, and delete or revert any file that was created on the discarded branch.
4. Rewind to the last ACCEPTED entry before N. That is the resume point.
5. Re-derive forward from there with the correction in hand. New assumptions get new numbers — never reuse a discarded entry's number.

**Never keep a discarded piece because it still looks useful.** Work derived from a rejected premise is a fossil, and a design carrying a fossil is worse than one built twice, because nobody can tell later which parts were reasoned and which survived by accident.

**Partial rejection.** The user accepts the direction but changes a detail. That is not a rollback: mark the entry ACCEPTED with the correction written into it. Then walk the downstream entries once and check each one still holds under the corrected version. Any that does not is a rejection, and the rollback above applies to it.

## Three paths

Classify the request first and say the classification out loud, so the user can override it:

- **Spike** — a feasibility question whose output is an answer, not code anyone keeps. Say the question and how you will probe it in two or three sentences, then go find out. A gate only if the probe itself costs real work or touches shared state. Report a recommendation, and label anything you built as throwaway.
- **Bounded** — a well-scoped change to a flow that **already exists in this repo**. Not "I understand this kind of app" — the flow you are changing has to be here to read. Explore, assume, present a short design in chat, **one gate**, implement.
- **Architectural** — a new project, a new subsystem, or a change that restructures how pieces fit or alters an interface others depend on. The full path below.

In doubt between two, take the heavier one. The ratchet is one-way: complexity discovered mid-task upgrades the path, and nothing downgrades mid-task.

### Bounded path

1. **Explore.** Files, docs, recent commits, the flow being changed. Answer everything you can without asking.
2. **Assume.** Open the ledger with what the repo did not settle.
3. **Design in chat.** Approach, files touched, how it gets tested. A few sentences to a few short paragraphs.
4. **One gate.** The design plus every open assumption, in a single batch.
5. **Implement.** Normal workflow, TDD where the project uses it. No plan document.

### Architectural path

1. **Explore.** Same as above, wider — how the existing pieces fit, what the interfaces are.
2. **Batch the questions that matter.** Purpose, constraints, success criteria, the choices the repo cannot answer. Four at a time, not one per message.
3. **Approaches and design, in one pass.** Two or three approaches with trade-offs and your recommendation, and the design that follows from the recommended one. Architecture, components, data flow, error handling, testing — each section scaled to how much it actually needs, not padded to look thorough.
4. **One gate on the whole design.** Not section by section. If the design is large enough that one gate cannot carry it, that is a signal the work needs decomposing into sub-projects, each with its own cycle.
5. **Write the spec.** `docs/specs/YYYY-MM-DD-<topic>-design.md`, or wherever the project puts them.
6. **Self-review the spec.** Placeholders and TBDs, sections that contradict each other, requirements open to two readings, scope that is really two projects. Fix inline, do not re-review.
7. **One review gate.** Ask the user to read the spec. Changes requested means fix and re-run step 6.
8. **Hand off to planning.** The written plan is the next artifact, not the code.

## The gate that never goes away

Batching changes **when** the user is asked, never **whether**.

Exploration and design run on assumptions. Implementation does not: production code gets written after the design that produced it was accepted. Nothing is committed and nothing is pushed without an explicit request, the same as everywhere else in this plugin.

If a task genuinely has no design worth stating, it did not need this skill.

## Red flags

| Thought | Reality |
|---------|---------|
| "I'll ask, it's faster than reading the code" | It is faster for you and slower for them. Go read it. |
| "I'll gate here to be safe" | Safety is the rollback, not the gate. If it is cheap to redo, keep going. |
| "Four assumptions are open but they're all small" | Count, not size. Four open means gate. |
| "They rejected #2 but #4 still stands on its own" | It rests on #2. Check the column, not your memory. |
| "I'll keep the file I wrote, it's most of the way there" | It came from a rejected premise. Delete it and say you did. |
| "They approved the design, so I can commit" | Approval of a design is not approval of a commit. |
| "I understand this kind of app, so it's bounded" | Bounded measures the repo, not your familiarity. No existing flow means architectural. |
| "It grew, but I'm nearly done" | Hidden complexity upgrades the path mid-task. Stop and say so. |

## When NOT to use

- **The task is already specified.** A spec or a written plan exists — execute it, do not redesign it.
- **Debugging.** A bug with an unknown cause is systematic debugging, not design.
- **The user asked for a specific change to a specific file.** That is the change, not a brainstorm.
- **Reviewing something that already exists.** `/soffner:self-review` and `/soffner:receiving-code-review` handle that side.
