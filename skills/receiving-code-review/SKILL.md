---
name: receiving-code-review
description: Use when review feedback arrives and has to be acted on - a human reviewer on a PR, an inline comment thread, the findings of `/soffner:self-review`, or a suggestion pasted into chat - or when the user invokes `/receiving-code-review`. Triages every item by whether changing the code buys anything real, implements the ones that do, declines the ones that do not with technical reasoning, and never performs agreement.
---

# receiving-code-review

Review feedback is a set of **hypotheses about the code**, not a list of instructions.

The default is not "implement unless I can prove it is wrong". The default is **implement when the change buys something real**. An item that is technically correct and buys nothing is a decline, and saying so is the job — an author who applies every suggestion is not being rigorous, they are being agreeable at the project's expense.

Verify before implementing. Ask before assuming. Technical correctness over social comfort.

## Order of operations

```
1. READ      every item, all the way through, without reacting
2. CLARIFY   anything unclear — all of it, before touching any code
3. VERIFY    each item against what the codebase actually does
4. TRIAGE    a verdict per item, in a table, before the first edit
5. IMPLEMENT the ones that earned it, one at a time, testing each
6. REPLY     in the thread, with the reasoning for every decline
```

Nothing gets edited before step 4 exists in writing. Triage after the fact is rationalisation.

## Step 2, unclear items block everything

```
IF any item is unclear:
  STOP — implement nothing yet
  ASK about the unclear items, batched into one message
```

Items are usually related. Implementing the four you understood before asking about the two you did not is how you implement the four wrong. Ask about all of them at once, not one per message.

## Step 3, verify against the codebase

Before an item can be triaged, know whether it is even true here:

- Does the code actually do what the reviewer thinks it does?
- Is there a reason the current implementation is the way it is — a commit, a comment, a test, a compatibility constraint?
- Does the suggestion break something that works today?
- Does it hold on every version, platform or tenant this project supports?
- Did the reviewer see the whole context, or the diff through a keyhole?

Cannot verify something: say so plainly and ask for direction. Do not implement a change you were unable to check.

## Step 4, the triage

Every item lands in one of three buckets **before** the gain test is even relevant.

**Free pass — implement, no further argument.** Correctness bugs, security holes, data loss, crashes, races, a broken documented contract, a broken test. The gain is self-evident. Do not spend a paragraph justifying the obvious.

**Decline by default.** Style with no rule behind it, "I would have written it differently", speculative generality, a feature nobody called for, a refactor of code this PR never touched. These need an argument to be promoted, not an argument to be dropped.

**Everything else — apply the gain test.**

### The gain test

Four questions. Question 1 must be a yes, and question 4 must not be a no.

1. **What breaks if we do not do this?** Name the concrete failure — an input, a caller, a user path, a future maintainer who is genuinely misled. "It is cleaner" is not a failure. If you cannot write the failing scenario in one sentence, there is no gain.
2. **Is the gain observable?** A bug that stops happening, a caller that stops being wrong, a cost you can measure, a contract that becomes checkable. Taste is not observable.
3. **What does the change cost?** Diff size, blast radius, regression risk, files dragged in from outside the PR, a re-test of a flow already validated, another review round, another day the PR sits open.
4. **Is it in scope for THIS PR?** A correct improvement to code this PR did not touch is a follow-up, not a change. Scope creep is the most common way a PR that was ready stops being ready.

**Verdicts:**

| Verdict | When |
|---------|------|
| `implement` | Free pass, or the gain is concrete and bigger than the cost |
| `decline` | No observable gain, or the cost exceeds it, or it is wrong for this codebase |
| `follow-up` | Valid and worth doing, outside this PR's scope |
| `blocked` | Cannot be decided without something you do not have |

Being right is not the same as being worth it. An item that is correct in principle but costs rewriting a module this PR barely touched is a `follow-up` or a `decline`, and saying that is a technical answer, not a dodge.

### Output before any edit

```
| # | Item | Verdict | Why |
|---|------|---------|-----|
| 1 | <one line> | implement | <the failure it prevents> |
| 2 | <one line> | decline | <no observable gain, or cost that exceeds it> |
| 3 | <one line> | follow-up | <valid, outside this PR's scope> |
| 4 | <one line> | blocked | <what is missing to decide> |
```

## Where the feedback came from

**From the user.** They decide the scope of their own work, so their items are not filtered out by the gain test. What the test still buys them is a warning: if an item costs more than it returns, **say so once**, with the number — the files it drags in, the flow it forces a re-test of. Then, if they confirm, implement it in full without relitigating. Stating a cost is useful; arguing twice is not.

**From an external reviewer.** Skeptical, but check carefully. Verify first, triage second, and push back in the thread when the verdict is `decline`. An item that contradicts a decision the user already made is `blocked` — take it to them rather than quietly overriding either side.

**From `/soffner:self-review`.** The findings table is already structured, which makes it tempting to implement top to bottom. It is a review like any other and gets the same triage. A finding that survived a Panel and a Judge is still a hypothesis about the code.

## Step 5, implementation order

1. Blocking first — breakage, security.
2. Then the cheap ones — typos, imports, dead code.
3. Then the ones with actual surface — refactors, logic.

One item at a time, tested individually. A batch of six changes tested once tells you the suite passes, not which of the six was safe.

Infrastructure failure while testing — database, fixtures, environment — goes back to the user with the exact message. Do not repair the environment to make a review item land.

## Step 6, how to say it

**Declining:**

```
✅ "Checked — build target is 10.15+, this API needs 13+. Keeping the legacy path."
✅ "Grepped for callers, this endpoint has none. Removing it instead of implementing it properly."
✅ "Valid, but it rewrites the serializer this PR only reads from. Opened as a follow-up."
```

Technical reasoning, evidence, no defensiveness. If pushing back out loud feels uncomfortable, name the tension and say the thing anyway — that discomfort is not a signal you are wrong.

**When the item is correct:**

```
✅ "Fixed. <what changed>"
✅ "Good catch — <the specific issue>. Fixed in <location>."
✅ <just fix it, the diff says it>

❌ "You're absolutely right!"
❌ "Great point!" / "Excellent feedback!"
❌ "Thanks for catching that!" — or any other thanks
❌ "Let me implement that now" (before verifying)
```

No gratitude. The fix is the acknowledgement. About to type "Thanks" — delete it and state the fix instead.

**When you pushed back and were wrong:**

```
✅ "You were right — checked <X> and it does <Y>. Implementing."
```

One line, factual, then move on. No apology, no defence of why you pushed back, no post-mortem.

**On GitHub**, reply inside the comment thread, not as a top-level PR comment:

```bash
gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies -f body='<reply>'
```

Replies posted to a pt-BR project are written in pt-BR — the payload follows its destination, while this skill stays English.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Performative agreement | State the requirement, or just act |
| Implementing because the reviewer is senior | Seniority is not the gain test |
| Implementing because the item is small | Small and pointless is still pointless |
| Verifying nothing and applying everything | Check against the codebase first |
| Triaging after the edits | The table comes before the first edit |
| Batch of fixes, one test run | One at a time, tested each |
| Accepting scope creep to seem accommodating | `follow-up` is a real verdict |
| Declining silently | Every decline gets its reasoning, in the thread |

## When NOT to use

- **Producing a review** rather than receiving one — that is `/soffner:self-review`.
- **The user gave a direct instruction** that happens to be about code. That is a task, not review feedback.
- **The feedback is about text**, not code — `/soffner:polish-text`.
