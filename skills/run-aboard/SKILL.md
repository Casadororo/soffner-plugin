---
name: run-aboard
description: Use ONLY when the user explicitly invokes `/run-aboard`, or when a `/loop` this skill scheduled fires it. Never auto-trigger from a mention of aboard or of a board. Starts this session as the orchestrator of an aboard board - resolves the board from a link or a name, records the WIP (default 2), takes cards up to it and delegates each one to a background agent (`claude --bg`), then keeps an hourly loop that is also the board's heartbeat.
---

# run-aboard

```
/run-aboard <board link or name> [wip, default 2]
```

Turns this session into the **orchestrator** of an aboard board. The board itself says how to run it: `use_board` returns a `usage` text (pt-BR) with the whole flow, columns, repository, gates and loop. That text is the spec. This skill only fills in what the text leaves to "your environment": the arguments, how agents are launched, how to find them again, and how the loop is scheduled.

You watch the board. You never implement a card yourself.

## 1. Resolve the board

- A link (`https://aboard.v360.io/boards/<slug>` or `.../boards/<slug>/cards/<id>`): the slug is the path segment after `/boards/`.
- Anything else is a name: `list_boards` and match it against `slug` and `name`, ignoring case and accents. One match: use it. Several: list them and ask. None: say so and stop.

## 2. Record the WIP and read the usage

`use_board(board: <slug>, wip: <arg, or 2 when omitted>)`.

The usage text says to ask the user for the WIP before anything. The argument **is** that answer: do not ask. Read the whole `usage` and follow it for everything below this skill does not override.

## 3. Schedule the loop (first run only)

Check `CronList`. If no job already runs `/soffner:run-aboard <slug>`, start one:

```
Skill loop, args: "<interval from the usage, 1h today> /soffner:run-aboard <slug> <wip>"
```

Each round re-runs this skill, so the usage text is reloaded fresh every hour, even after the context was compacted. The job already existing means this invocation **is** a round: skip straight to step 4.

## Ownership: only the cards this orchestrator took

aboard knows the **user**, not the session. "Assigned to you" is every card any session of this user holds: another orchestrator, an interactive session, an agent waiting on an approval. So this skill overrides the usage text's "prefer a card already assigned to you". It owns only the cards in its ledger:

```bash
LEDGER="${XDG_RUNTIME_DIR:-/tmp}/aboard/<slug>.cards"   # one card id per line
```

- `take_card` only a card that is **free** (no assignee) or already in the ledger, and append its id to the ledger right after.
- A card assigned to the user but not in the ledger belongs to someone else. Never take, test, relaunch, stop or move it. On the first run, list those cards with their column and ask which to adopt; adopted ids go into the ledger. Later rounds only show them in the round table as `other session`.
- A card that reaches DONE leaves the ledger.

One orchestrator per board: the ledger is per board, so a second one would claim the same cards.

## 4. A round

1. Reconcile first (below), then take cards until occupation reaches the WIP, in the order `use_board` lists them (NEEDS FIX first), skipping any card the ownership rule excludes.
2. `take_card(card_id)` returns the briefing. Write it to a file and launch the agent from the local clone of the repository the usage names for that card (tag exceptions included). No local clone found: comment on the card, move it to ON HOLD, and tell the user which repo is missing.

   ```bash
   DIR="${XDG_RUNTIME_DIR:-/tmp}/aboard"; mkdir -p "$DIR"
   # briefing text from take_card goes into "$DIR/<card id>.md"
   cd <local clone> && claude --bg -n "aboard #<card id> <two-word subject>" \
     --model opus --effort high \
     "Read $DIR/<card id>.md and carry out the card end to end, as its text says."
   ```

3. A ledger card the implementation agent moved to NEEDS MANUAL TEST gets the separate, light test agent the usage asks for. Same launch, from the PR's worktree, with `-n "aboard #<card id> test"`, `--model sonnet`, and a prompt that points at the card and the manual test section of the usage.
4. Print the round to the user in one short table: card, column, agent, state. Then stop until the next round.

## Reconcile

Agents are found by name, so the name format above is load-bearing:

```bash
claude agents --json | python3 -c "
import json,sys
for a in json.load(sys.stdin):
    if (a.get('name') or '').startswith('aboard #'): print(a['id'], a['state'], a['name'])
"
```

Reconcile only ledger cards.

- A ledger card in DOING, or a test round in NEEDS MANUAL TEST, with **no** `aboard #<card id>` agent at all: check the PR (`gh pr list --search <card id>`, or the link in the card's comments) before relaunching. The session may have finished without reporting. An agent that exists in any state other than `done` is alive: idle or blocked means it waits on a human, not that it died.
- An agent in state `done` whose ledger card already moved on: `claude stop <id>` so it stops holding memory.
- An agent stuck on an approval prompt is not fixed by messaging it: stop it, clean its side effects, relaunch with the briefing reinforced (the usage says the same).

## Card comments are pt-BR

Every `comment_card` this skill writes goes to the pt-BR team, so it is written in pt-BR (the plugin's publish exception). Terminal output to the operator stays English.

## Stopping

Only when the user says so: delete the loop job (`CronDelete`), and leave the agents running unless they ask to stop them too.
