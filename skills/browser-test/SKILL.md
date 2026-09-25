---
name: browser-test
description: Use ONLY when the user explicitly invokes `/browser-test`. Never auto-trigger from keywords, and never start a browser or a dev server because a change "should be checked visually". Validates an already-open pull request by exercising what it delivered in Chrome (Claude in Chrome MCP) against a dev server running from the PR's own worktree, with a permission gate on anything that changes the database beyond what a user of the feature would do.
---

# browser-test

Prove in the browser that a pull request does what it says. Read the delivery, bring up the server from the PR's worktree, drive Chrome through every delivered behavior, and hand back a report with evidence.

**The invocation authorizes the browser and the web server. It does not authorize touching the database to make a test possible.** Doing what a user of the feature would do is free, and so is flipping the flag the PR itself ships. Reaching past the feature to bend unrelated data, settings or flows so the feature has something to show is a gate, every time.

**Nothing is torn down on its own.** The server stays up and every setting stays where the last row left it until the user answers the teardown question in step 8. The point of running this is often to hand over a working environment and keep clicking by hand.

## Arguments

`/browser-test [pr]`

| Token | Rule |
|-------|------|
| `pr` (optional) | `123`, `#123`, a GitHub URL or a branch name. Missing: the PR of the current branch (`gh pr view --json number,headRefName`). No PR on the current branch either: ask which PR and stop. |

## Authorization contract

Free, no question asked:

- Detecting or starting the **web server** of this worktree, with whatever command the project documents, and reading its development log.
- Everything a signed-in user does **through the browser** to exercise the PR, including creating **new** user-level records the feature needs (a report in the report builder, a filter, a dashboard card). Name each one with the prefix `TESTE_` and note its id. A new configuration entity (process flow, setting, role, trigger) is not a user-level record: creating one fresh is still the configuration gate.
- Reading the database: `bin/rails runner` that only reads, `psql` with `SELECT`, `Model.count`.
- Screenshots, GIFs, console and network reads.

Gated, one `AskUserQuestion` per action, before the action:

| Gate | Covers |
|------|--------|
| Write outside the browser | any `rails runner` or `psql` that writes, `db:migrate` on the dev database (pending migration is this gate, not a fix), `db:seed` |
| Pre-existing record | persisting any change to, or deleting, a record that existed before this session, through the UI or otherwise. Only `TESTE_` records created in this run are yours. An interaction on an existing record counts as a read only when `read_network_requests` shows no write request during it |
| Environment configuration | permissions, roles, process flows, triggers, integrations, and every setting except the flag the PR ships or reads (see [Settings](#settings)); anything that changes how the environment behaves so the test can proceed |
| Background processes | job workers, schedulers, anything that consumes a queue shared with other worktrees |

Gate question shape, always the same three parts:

```
question: "<action> on <target> is needed to test <map row>. Allow?"
body:     what changes (model, id, field, current value, new value), why the row cannot run without it, how it gets undone
options:  "Allow" | "Skip this test" | "Allow, I will undo it myself"
```

"Skip this test" is an answer, not a problem: mark the row `blocked: needs <action>` and go on. Never look for a second route to the same change. The user drew these lines on purpose, and the report of what could not be tested is part of the deliverable.

A gate discovered mid-run does not stall the map: park the row as `blocked: awaiting answer`, finish every row that does not depend on it, then ask all parked gates in one question at the end and re-run the rows that were allowed. A gate still unanswered when the report is written stays `blocked: awaiting answer` in it.

## Settings

A setting is the most common precondition a PR needs, so the method is fixed for the whole run. Do not invent a route per run, and read the project's own rules before opening an admin screen in dev: an admin UI that is fine in production can be the one page that takes the dev server down, and a value changed through a screen leaves no `before` to restore.

Which settings are yours to change:

| Setting | Rule |
|---------|------|
| The flag the PR itself ships or reads | Free. It is the on/off switch of what is under test, in both directions: turning it on to reach the feature and off to check the fallback are equally part of the delivery. |
| Anything else | Gate, one question, before touching it. |

"The PR ships or reads it" is a fact you show, not a feeling: the key appears in `gh pr diff`, or the code path under test reads it at a `file:line` you cite. Without that evidence the setting is unrelated, and unrelated goes through the gate even when it is the shortest path to a green row. The dev database is shared by every worktree on the machine, so an unrelated flag changes what other people's servers do, which is exactly what the operator asked to be consulted about.

Find the key in the code, never by guessing the name. Grep the definition, not a usage, so the group or namespace it belongs to comes with it, and cite the `file:line` you found it at.

Then read it, change it and prove it **in one command**, through whatever setter the project exposes outside tests:

```
before = <read the setting>
saved  = <write the setting>
after  = <read it again>
print before, saved, after
```

Four things that shape pins down, and each one has bitten a run:

- **The documented setter is the only one.** Frameworks often ship a second, test-only writer that raises or silently no-ops outside the test environment. Find which one the project sanctions before writing.
- **Preconditions of the setter come first in the same command.** A per-account or per-tenant application needs the current account established before a read even works, and the error it raises otherwise looks nothing like "you forgot the account".
- **A bang in the name does not mean it raises.** A setter that ends in `save` rather than `save!` returns `false` on a validation failure and changes nothing, silently. `saved` false, or an `after` equal to `before`, means it did not happen. Do not run the row as if it had.
- **`before` is unreadable once the write lands.** It is what the report shows and what the teardown question offers to put back, so capture it in the same command that changes the value.

The running server does not see the new value right away. Settings are commonly cached per process with a coarse refresh window, so the browser can keep serving the old value for minutes after the command printed the new one. Check the project's cache window, reload once, then wait it out. Do not edit a file to make the reloader drop the cache: code is frozen while the map runs.

Every setting this run changed gets logged the moment it changes: group, name, `before`, `after`. That log is the report's `Settings changed` table and the only list step 8 is allowed to offer to restore.

## Flow

1. Resolve the PR and land in its worktree.
2. Read the delivery and build the test map.
3. Find or start the server.
4. Open Chrome and get signed in.
5. Run the map, row by row.
6. Collect evidence.
7. Report.
8. Ask what to tear down.

### 1. PR and worktree

```bash
gh pr view <pr> --json number,title,url,state,headRefName,baseRefName,isDraft,changedFiles
git branch --show-current
```

Current branch equals `headRefName`: continue here. Anything else means this session is not in the PR's worktree. Invoke `/soffner:dono <number>` with no task, let it create or enter the worktree and sync, then continue from step 2 inside it. Never test a PR from a checkout of another branch, and never `git switch` inside a worktree that holds something else.

Record the SHA under test: `git rev-parse --short HEAD`. It goes in the report, because the server serves this commit and nothing else.

### 2. Test map

Read all of it before touching the browser:

```bash
gh pr view <number> --json body,commits --jq '.body, (.commits[] | .messageHeadline)'
gh pr diff <number>
gh pr view <number> --json files --jq '.files[].path'
```

From the body (a "Como testar" section when it exists), the commit headlines and the diff, write the map: one row per delivered behavior a user can reach.

```
| # | Behavior | Screen / route | Steps | Expected | Needs |
```

`Needs` is where the gate shows up early: `none`, `new TESTE_ record via UI`, `setting <group>.<name> via runner` when the flag is the PR's own, or the gated action by name. Fill it by probing preconditions with free reads before printing the map (the flag on the flow, the setting's value, whether the data the screen lists exists), not by guessing. Rows whose `Needs` is gated get their question **now**, in one `AskUserQuestion` with `multiSelect`, so the run is not interrupted at every third click. Anything discovered later follows the parking rule in the contract.

Routes and views in the diff that the body does not mention still get a row. The body describes what the author remembered; the diff describes what shipped. Print the map to the user and proceed. It is information, not a gate.

### 3. Server

Only a server whose working directory is **this** worktree counts:

```bash
ROOT="$(git rev-parse --show-toplevel)"
for pid in $(pgrep -f '^puma [0-9.]+ \(tcp://'); do
  if [ "$(readlink /proc/$pid/cwd)" = "$ROOT" ]; then tr '\0' ' ' < /proc/$pid/cmdline; echo; fi
done
```

The pattern is anchored on purpose: an unanchored `pgrep -f puma` matches the shell running the loop, whose cwd is `$ROOT`, and reports a server that does not exist. The puma title carries the port (`tcp://localhost:3001`); extract it with `grep -oE 'tcp://[^)]+' | grep -oE '[0-9]+$'`. A match means reuse that port. No match means starting the project's dev server in the background from `$ROOT`, then reading the port it announces and waiting for `Listening on`. Servers of other worktrees stay untouched: they serve other commits, and their port proves nothing about this PR.

Smoke test before any browser work:

```bash
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:<port>/"
```

`200` or `302` is alive. `500` with `Migrations are pending` in the log is the "write outside the browser" gate; if allowed, migrate and then restore every schema dump the migration touched, because migrating re-dirties them with churn that does not belong to the PR.

**`localhost`, never `127.0.0.1`.** An app that resolves the account or tenant from the hostname does not recognise the literal IP, and answers every route with its own 404 page, which looks exactly like a missing route.

### 4. Chrome

Load the tools in one `ToolSearch` call: `tabs_context_mcp`, `tabs_create_mcp`, `tabs_close_mcp`, `navigate`, `computer`, `read_page`, `find`, `read_console_messages`, `read_network_requests`, `gif_creator`.

**One tab for the whole run, and its id is settled before the first navigation.** Two calls each create a tab, and calling both is how a run ends up with a blank tab sitting next to the tab under test: `tabs_context_mcp` with `createIfEmpty: true` opens the group *and* an empty tab inside it, and `tabs_create_mcp` opens another. A standalone `navigate` without `tabId` then drives the group's **first** tab, which is not the one just created, so the evidence comes from one tab while the other stays empty.

The opening sequence, exactly:

1. `tabs_context_mcp` with `createIfEmpty: true`.
2. `TAB` is the id to use for everything after this: the empty tab that call just put in the group. Only when the group already existed with tabs of its own does `tabs_create_mcp` run, once, and `TAB` is the id it returns.
3. Every later browser call carries `tabId: TAB` — `navigate` included, every time, standalone or not.

`TAB` goes in the report's Environment line. If a second tab in the group turns up anyway, close it with `tabs_close_mcp` before the first row runs: evidence has to come from one known tab. Tabs outside the group are the user's and are never touched.

Navigate to `http://localhost:<port>`. A sign-in form means stop: name the tab and the URL, and hold on an `AskUserQuestion` with the single option "Signed in" until the user has signed in **in that tab**. The skill never types a password, never opens a credentials file (a stray one found on disk goes to the report's Notes, unquoted) and never resets a user's password to get past the form (that would be the pre-existing record gate anyway). Once `read_page` shows a signed-in user on the landing page, continue.

The browser is one resource: rows run one after the other, never in parallel, never from a subagent.

### 5. Running the map

For each row, in order:

1. `navigate` to the screen. Prefer `read_page` (accessibility tree) and `find` to locate elements; take a screenshot only when coordinates are needed or the state matters.
2. Do the steps as a user would.
3. Confirm `Expected` from `read_page`, not from a hunch about the screenshot.
4. `read_console_messages` with `onlyErrors: true` and `pattern: "Error|Uncaught|Failed"`. A JS error is a finding when the erroring asset is in the diff, even on a screen the PR did not list and even when the screen looks fine. Otherwise it is a Note, marked `not verified on base`.
5. Check the server side of the row: note `wc -l < "$ROOT/log/development.log"` before the row, and after it `tail -n +<that line> "$ROOT/log/development.log" | grep -nE 'Completed 5[0-9]{2}|Error|Exception'`.
6. Mark the row `pass`, `fail` or `blocked`, with the evidence file names. A row that cannot run because an earlier row failed is `blocked: upstream fail #<n>`, not `fail`.

Rules while the map runs:

- **Code is frozen.** Rails reloads on every edit, so a fix mid-run changes the app under the remaining rows and the evidence stops describing the PR. A bug is a finding with a suspected cause confirmed by reading the code (`file:line`), not a fix. Fixing is a separate request.
- **A `fail` gets reproduced once** before it goes in the report. Same steps, fresh navigation. A single occurrence with no reproduction is reported as `flaky, seen once`.
- **Desktop viewport only** unless the user asks for mobile. `resize_window` does not reliably change the page's inner width on this machine; a mobile check needs a same-origin iframe of the target width, and that is its own request.
- **Extra coverage is welcome, extra reach is not.** Creating a `TESTE_` report to test a new column is coverage. Changing the flow that feeds the report so the column has data is reach, and it is the configuration gate.

### 6. Evidence

Evidence lives in the worktree, gitignored:

```bash
EVIDENCE="$ROOT/tmp/browser-test/pr-<number>"
mkdir -p "$EVIDENCE"
```

- Screenshot with `computer` `screenshot` and `save_to_disk: true`; copy the returned path to `$EVIDENCE/<nn>-<row-slug>.png`. One per row at least, one more per finding showing the broken state.
- A row with three or more steps may get a GIF: `gif_creator` `start_recording` before the first step, `stop_recording` after the last, `export` with `download: true` and a `filename` of `<nn>-<row-slug>.gif`; move it from the downloads folder into `$EVIDENCE`.
- Write `$EVIDENCE/REPORT.md` with the same content as the chat report below, plus the full test map.

No credential, token or password ever goes into a file under `$EVIDENCE`.

### 7. Report

Fixed shape, in the chat and in `REPORT.md`:

```
## browser-test: PR #<number> <title>

Environment: <worktree path>, <sha>, http://localhost:<port>, server <reused|started>, Chrome tab <TAB>
Map: <n> rows, <p> pass, <f> fail, <b> blocked

### Findings
| # | Row | What happens | Evidence | Suspected cause |
(one line per fail; cause as file:line confirmed in the code, or "not located")

### Passed
| # | Behavior | Evidence |

### Blocked
| # | Row | Reason | Answer |
(`needs <gated action>` with the user's answer, `awaiting answer`, or `upstream fail #<n>`)

### Records created
| Model | id | Name |
(all TESTE_ records, left in place for the environment owner to clean)

### Settings changed
| Group.name | Before | After | Restored |
(only settings this run changed; `Restored` filled in step 8)

### Gates asked
| Action | Target | Answer |

### Notes
(observations outside the map: console errors on untouched screens, stray files on disk, anything the user should know that is not a verdict on the PR)

### Teardown
(server kept on <port> or stopped, which settings were put back, TESTE_ records left in place)
```

The report goes out before the teardown question, so the evidence survives even if nobody is at the keyboard to answer. Step 8 then fills the `Restored` column and the `Teardown` line, in the chat and in `REPORT.md`.

Nothing gets committed, nothing gets pushed, no comment goes to the PR. The evidence folder is a work artifact; the user decides what leaves the machine.

### 8. Teardown

The run ends with the environment as the last row left it. The server keeps running, the settings keep their new values, and the browser keeps its session, until the user says otherwise. Most of the time this skill finishes and the operator wants to carry on clicking in that same tab, and an automatic cleanup throws away the sign-in, the port and the preconditions that took the whole run to line up.

So teardown is one `AskUserQuestion` with `multiSelect`, offering only what this run actually touched:

| Offer | When it appears | Options |
|-------|-----------------|---------|
| The server | only if this run started it | `Keep it running on <port>` (first, recommended) or `Stop it (pid <pid>)` |
| One row per setting this run changed | one per line of the `Settings changed` table | `Restore <group>.<name> to <before>` or `Leave it at <after>` |
| Chrome tab `<TAB>` | always | `Keep the tab open` (first) or `Close it` |

Three limits on that question:

- **A server this run did not start is never offered.** It belongs to whoever started it, it keeps serving whatever it serves, and it is not mentioned beyond the report's Environment line.
- **Only settings this run changed are offered.** Restoring means back to the `before` this run captured, never to the schema default: a setting that was already off default when the run started is somebody else's decision on a database every worktree shares, and "fixing" it is a change nobody asked for.
- **`TESTE_` records always stay.** They are prefixed for exactly this reason, and deleting a record is the pre-existing-record gate looked at from the other side.

Nothing changed and nothing started means no question: say the environment was left untouched and stop.

If the question goes unanswered, everything stays up and the `Teardown` line records `not answered, environment left as is`. Leaving a usable environment behind is the safe failure; a silent cleanup is not.

## Rationalizations that mean stop

| Thought | Reality |
|---------|---------|
| "It is one setting, I will flip it back after" | Unless the PR ships or reads that flag, the dev database is shared by every worktree on the machine and flipping it changes what other running servers do. Gate. And putting it back is the step 8 question, not your call. |
| "The map is done, I will stop the server and put the settings back" | Teardown is a question, never an action. The operator usually keeps testing by hand in that tab, on that port, with those preconditions. |
| "This setting is off its schema default, I will fix it while I am here" | Only what this run changed is yours to restore, and only to the value this run found. |
| "I will find the setting in the admin panel" | Some admin screens take the dev server down, and a value changed through a screen leaves no `before` to restore. Use the command recipe in Settings, or the gate. |
| "The setter has a bang, so it raised if it failed" | A bang that ends in `save` returns `false` and changes nothing. Read the value back. |
| "The user wants the test to pass, they would obviously allow this" | The user chose which actions need asking. The question is the deliverable, not an obstacle to it. |
| "Editing it through the UI is what a real user would do" | A user of the feature creates new things. Changing something that existed before this session is the gate, UI or runner. |
| "A runner is faster than five screens of clicking" | Reads through the runner are free. Writes go through the browser or through the gate. |
| "The fix is a one-liner, it saves a round trip" | Dev reloads under the running rows and the evidence stops matching the PR. Report, do not fix. |
| "There is already a server on 3000, I will use it" | Its cwd is another worktree, so it runs another commit. Detect by cwd, or start your own. |
| "127.0.0.1 is the same as localhost" | Account resolved by host. The IP gets the 404 page on every route. |
| "I will open the group, then create the tab for the run" | `tabs_context_mcp{createIfEmpty: true}` already left an empty tab in the group. `tabs_create_mcp` on top of it is the second tab, and a `navigate` with no `tabId` then runs the test in the first one. One tab, settled in step 4. |
| "navigate resolves the tab on its own, I can drop the tabId" | It resolves to the group's first tab, not to the tab this run picked. Pass `tabId: TAB` on every call. |
| "I will type the password from the credentials file, it is local" | Never. Ask the user to sign in in the tab. |

## When NOT to use

- The PR is not open yet, or the change is only in the working tree: nothing to validate against a delivery. Open the PR first.
- API or token flows with no screen: this skill drives a browser, so request-level testing belongs to whatever the project uses for it.
- Review of the diff itself: `/soffner:self-review`.
- Recording a demo of a PR for the team: `/soffner:demo`, which plans the route, films it and publishes it in the PR body.
