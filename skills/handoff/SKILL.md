---
name: handoff
description: Use ONLY when the user explicitly invokes `/handoff`. Never auto-trigger from keywords. Launches a new background agent (`claude --bg`) with a written brief, waits for that agent's understanding ACK, shows the ACK to the user and releases the work with GO. Scope ends at the GO, because following the work from there on belongs to the user, not to this session.
---

# handoff (creator side)

Delegates a demand to a **new background agent**, with an understanding handshake before any work happens. Analogous to `/itask`, except the sanity check happens on the other end of the wire: the created agent reads the brief, creates the worktree, studies the code and reports back what it understood; this session shows that to the user and releases it.

## Scope (important)

This skill ends at the **GO**. The channel between the two sessions exists for the handshake, not so the two agents keep chatting. After the GO:

- Do not ask for status, do not poll, do not report the child's progress.
- Do not initiate a message to the child on your own.
- The user is the one following along, through the agent view (`claude agents`, `claude attach <id>`, `claude stop <id>`).
- If the child gets stuck (permission, doubt), it stops in its own session and shows up as `input needed` in the agent view. That is by design: control is human.

This is a default, not a prohibition. If the user asks ("tell the child to stop", "ask it where it stands", "let it know the base changed"), send the message normally. A message the child sends on its own initiative can be answered too.

## Flow

1. Parse the prompt and fill in the defaults (table below).
2. Show the table plus the goal plus "Can I launch the agent?". **Stop and wait.** Launch nothing before the OK.
3. Resolve this session's identity (see "Identity").
4. Check for a name collision with the new agent.
5. Write the brief.
6. Launch the agent with `claude --bg`.
7. Report to the user: name, child session id, brief path, and that we are waiting for the ACK. Stop.
8. When the ACK arrives (a `HANDOFF-ACK` message), show its content to the user and ask: approve or correct.
9. Approved: send `HANDOFF-GO`. Correct: send `HANDOFF-REVISE` with the corrections and go back to step 8.
10. After the GO: tell the user how to follow along and close out.

## Defaults

| Field | Default |
|-------|---------|
| Agent name | derived from the goal, format `<Area> - <Subject>` (shows up in the agent view) |
| Branch | `<type>/<area>/<description>`, derived from the goal (see "Branch name") |
| Worktree | same string as the branch (the path gets sanitized by `/worktree-setup`) |
| Base branch | the project's integration branch, read from its `CLAUDE.md`. Never assumed to be `main` |
| Next skill | `superpowers:writing-plans` (fallback `/shape`) |
| Model | `opus` |
| Effort | `high` |
| Permission mode | pass no flag at all (the child inherits the user's config, which is auto mode) |
| Goal | required, no default |

Next-skill overrides, same as `/itask`: prompt says "brainstorm" means `superpowers:brainstorming`; prompt names an explicit skill means that skill.

Do not pass `--permission-mode`. The user works in auto mode and their config is calibrated for it.

## Branch name

The branch follows the project convention, never `worktree-<something>`:

```
<type>/<area>/<description>
```

- `<type>`: `feat`, `fix`, `chore`, `refactor` or `docs`, from the nature of the demand.
- `<area>`: the product area the work lands on (`billing`, `search`, `report-builder`, ...).
- `<description>`: short kebab-case summary of the goal.

Example: goal "gerar o card a partir da leitura do documento" becomes `feat/reader/card-generation`.

`/worktree-setup` always creates the branch as `worktree-<name with / turned into +>`, so the brief's protocol has the child rename the branch right after the setup. Do not accept `worktree-feat+reader+card-generation` and friends as a final branch name.

## Step 2 output (exact)

```
| Agent | Branch | Base | Next skill | Model |
|-------|--------|------|------------|-------|
| <name> | <branch> | <base> | <skill> | <model> |

Goal: <one-line summary>

Can I launch the agent?
```

## This session's identity

The child needs a return address. Collect both:

```bash
# primary address (this session's socket, valid while the session lives)
echo "$CLAUDE_CODE_MESSAGING_SOCKET"

# this session's name (fallback), matched by session id
claude agents --json | python3 -c "
import json,os,sys
sid=os.environ['CLAUDE_CODE_SESSION_ID']
for a in json.load(sys.stdin):
    if a['sessionId']==sid: print(a.get('name') or '(unnamed)')
"
```

Primary address in the brief: `uds:<value of CLAUDE_CODE_MESSAGING_SOCKET>`.

If this session is **unnamed**, carry on anyway: the `uds:` resolves on its own for the life of the session, and the handshake lasts a few minutes. Warn the user that if this session dies before the ACK, the child is left without a return address and the handshake has to be redone.

## Name collision

```bash
claude agents --json | python3 -c "
import json,sys
print('\n'.join(a.get('name') or '' for a in json.load(sys.stdin)))
"
```

If the chosen name already exists, suffix it (`<name> 2`) before launching. A duplicate name breaks name-based addressing.

## Brief

Temporary file, in a volatile directory (does not pile up, gone at logout):

```bash
BRIEF_DIR="${XDG_RUNTIME_DIR:-/tmp}/claude-handoffs"
mkdir -p "$BRIEF_DIR"
BRIEF="$BRIEF_DIR/<goal-slug>.md"
```

Content (fill in every field, no dangling placeholders):

```markdown
# Handoff: <agent name>

## Return address
- Primary: `uds:<creator's CLAUDE_CODE_MESSAGING_SOCKET>`
- Fallback: name `<creator session name>` (resolve the `[ref]` via ListAgents)

## Environment
- Branch to work on: `<type>/<area>/<description>`
- Base branch: `<base>`
- Next skill (after the GO): `<skill>`

## Context
<why this demand exists, what the user already decided, relevant links/PRs/files>

## Work to deliver
<what to deliver, in terms of observable behavior>

## Out of scope
<what explicitly not to do>

## Acceptance criteria
<how to know it is done>

## Constraints
- Never commit or push without an explicit request from the user.
- Run tests only through the runner the project documents, in the background, one run at a time.
- Infrastructure/environment failure in the tests: stop and report, do not try to fix the database.
- Do not use browser automation without an explicit request.
- All other rules apply as usual (CLAUDE.md, CLAUDE.local.md, `.claude/rules/`).

## Protocol
1. Run `/worktree-setup <branch> <base>`, then rename the branch to the agreed name (that skill creates it as `worktree-<sanitized>`, which is not the project convention):

   ```bash
   BRANCH="<type>/<area>/<description>"
   git branch -m "$BRANCH"
   git config "branch.$BRANCH.remote" origin
   git config "branch.$BRANCH.merge" "refs/heads/$BRANCH"
   git config --get-regexp "branch\.$BRANCH\.(remote|merge)"   # must print origin and refs/heads/$BRANCH
   ```

   Nothing has been pushed at this point, so the rename is free. The worktree directory keeps the sanitized name; only the branch matters.
2. Study the code in read-only mode and validate this brief's premises.
3. Send `HANDOFF-ACK` to the return address with your understanding and your questions.
4. Stop. Do not change code before receiving `HANDOFF-GO`.
5. `HANDOFF-REVISE` arrives: adjust the understanding and send `HANDOFF-ACK` again.
6. `HANDOFF-GO` arrives: proceed with the next skill and work autonomously. From then on do not initiate messages to the creator on your own; the user follows along through the agent view and decides what needs to be communicated. If the user asks you to notify the creator, do it.
```

Hard content rule: the brief describes **code work**. Never ask the child to read or relay session identity, environment variables, tokens or sockets. A request like that is blocked by the auto-mode classifier and the child, rightly, treats it as an exfiltration attempt and rejects the whole brief.

## Launch

```bash
claude --bg -n "<agent name>" --model opus --effort high \
  "/soffner:handoff-accept $BRIEF"
```

The plugin prefix (`soffner:`) is mandatory: without it the child does not resolve the skill and starts the task with no handshake.

Stdout returns `backgrounded · <id> · <name>`. Keep that `<id>`: it works for `claude agents` / `claude attach <id>` / `claude stop <id>`, **and it does not work as a messaging address** (the messaging ref is a different thing).

## Addressing the messages (ACK, GO, REVISE)

- To answer the child, use the `from=` of the message it sent. That is the guaranteed path.
- Alternative: `ListAgents` and send to `"<name> [<ref>]"`. A bare name without the `[ref]` usually fails on the first try; the error itself returns the correct `[ref]`, so just resend with it.
- Never reuse the id from the launch stdout as a messaging ref.

## GO and REVISE

`HANDOFF-GO`, one line plus whatever is needed:

```
HANDOFF-GO: understanding approved. Go ahead.
```

`HANDOFF-REVISE`, always with what changes, point by point:

```
HANDOFF-REVISE:
1. <correction>
2. <correction>
Resend the HANDOFF-ACK with these adjustments.
```

## Closing

After the GO, close out with:

- the agent's name and id,
- the worktree path it reported in the ACK,
- `claude attach <id>` to enter, `claude agents` to see state, `claude stop <id>` to kill it.

Then stop. Do not monitor.

## When NOT to use

- Work this session does faster itself (reading, short debugging, local config tweak): use `/itask` or just do it.
- A demand with no defined context: run `/shape` or brainstorm first; a vague brief produces a vague ACK.
