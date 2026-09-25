---
name: browser-test-auto
description: Use ONLY when the user explicitly invokes `/browser-test-auto`, or when a board briefing names it. Never auto-trigger from keywords. Unattended version of browser-test. Takes a machine-wide lock, hands the run to one fresh Opus runner in the background that signs in as a temporary per-PR user and drives Chrome through everything the PR delivered without asking anything, restores every setting it changed, and returns the evidence. This session then audits every screenshot against what the runner claimed before reporting.
---

# browser-test-auto

`browser-test` asks before every write, so it needs someone at the keyboard. This skill runs with nobody there. The invocation replaces the questions with a fixed contract: what is inside it runs, what is outside it becomes a `blocked` row with its reason.

Two roles, one skill:

| Role | Who | Does |
|------|-----|------|
| Orchestrator | the session that invoked the skill | resolves the PR, takes the lock, dispatches the runner, audits the evidence, releases the lock, reports |
| Runner | one fresh subagent, Opus | builds the test map, brings up the server, prepares the temporary user, drives Chrome, saves evidence, restores settings |

The split exists for three reasons:
- **Context.** Screenshots and accessibility trees stay in the runner. The orchestrator is usually the session that wrote the PR and still has work to do.
- **A blind start.** The runner builds its map from the delivery. It never sees what the implementing session believes already works.
- **A second look.** The orchestrator judges from the saved evidence, not from the runner's word.

## Arguments

`/browser-test-auto [pr] [focus]`

| Token | Rule |
|-------|------|
| `pr` (optional) | The first token, when it is `123`, `#123`, a PR URL or an existing branch name. Missing: the PR of the current branch (`gh pr view --json number,headRefName`). None there either: `failed: no PR to test`. |
| `focus` (optional) | Everything else, free text from the operator ("check the empty state"), passed to the runner **verbatim**. It adds emphasis; the map still covers the whole delivery. |

## What the invocation authorizes

Free, for the runner and, during cleanup, for the orchestrator:

- Detecting or starting the web server of the PR's worktree. The invocation is the explicit request the project asks for before starting a server.
- Chrome, screenshots, console and network reads, the development log.
- Reading the database.
- Creating or refreshing **this PR's temporary user**, its `TESTE_` role and group, and its first-access marks ([Temporary user](#temporary-user-v360)).
- Creating any new record the map needs, through the UI or a runner, named with the prefix `TESTE_`, id logged.
- Changing **any setting**, only through the [Settings](#settings) recipe, logged before the write and restored before the lock is released.
- `db:migrate` on the dev database when migrations are pending, then restoring every schema dump the migrate touched (`git checkout -- <dump>`) and listing the versions in the report.

Outside the contract. The row becomes `blocked: <reason>`. Never look for a second route to the same change:

- Persisting a change to, or deleting, a record that existed before the run, through the UI or otherwise. An interaction on an existing record counts as a read only when `read_network_requests` shows no write during it.
- A new record that acts on existing data (trigger, integration, scheduled job, a flow attached to live records). Its effect is a change to existing data.
- Job workers, schedulers, anything that consumes a queue shared with other worktrees.
- Recreating a database: `db:reset`, `db:drop`, `db:schema:load`, `db:fixtures:load`, `db:seed`.
- Editing code in the worktree under test. Rails reloads, and the evidence stops describing the PR.
- Signing in as a real account, typing a real credential, opening a credentials file.

## The lock

Settings live in the dev database and Chrome is one browser, both shared by every worktree on the machine. Two runs at once flip settings under each other and fight over the tab. One run at a time, machine-wide.

The lock is a directory (`mkdir` is atomic) whose owner is the orchestrator's session process. `$PPID` of a Bash tool call is that process and stays the same for the whole session. The runner lives inside the same process, so it holds the lock through the orchestrator. Read `$PPID` at the top level of the Bash call, never inside `bash -c` or a script, where it is a different shell.

Acquire:

```bash
LOCK="$HOME/.cache/soffner-browser-test/lock"
mkdir -p "$(dirname "$LOCK")"
if mkdir "$LOCK" 2>/dev/null; then
  printf 'pid=%s pr=%s worktree=%s since=%s\n' "$PPID" "<pr>" "$ROOT" "$(date -Is)" > "$LOCK/owner"
  echo acquired
else
  cat "$LOCK/owner"
fi
```

Busy means reading the owner line:

| Owner | Action |
|-------|--------|
| `pid` equals `$PPID` | This session already holds it (a re-run after an interruption). Rewrite the owner line and continue. |
| `pid` is dead (`kill -0` fails) or the owner file is missing | Stale. `rm -rf "$LOCK"`, acquire again, and note in the report whose lock was taken over. |
| `pid` is alive | Wait. Run the loop below with `run_in_background`; exit `0` means acquire again, exit `1` is `failed: lock held by <owner line>`. |

```bash
LOCK="$HOME/.cache/soffner-browser-test/lock"
for _ in $(seq 120); do
  [ -d "$LOCK" ] || exit 0
  kill -0 "$(sed -n 's/^pid=\([0-9]*\).*/\1/p' "$LOCK/owner" 2>/dev/null)" 2>/dev/null || exit 0
  sleep 30
done
exit 1
```

Release is the last thing before the final report, on every path, failure included, and only when the owner `pid` is still `$PPID`:

```bash
LOCK="$HOME/.cache/soffner-browser-test/lock"
grep -q "^pid=$PPID " "$LOCK/owner" && rm -rf "$LOCK" && echo released
```

A live lock is never deleted because it looks old: the owner may be halfway through a row.

Skills that do not know this lock (`browser-test`, `run-manual-tests`) are not held off by it. Do not run them on this machine while a run holds it.

## Orchestrator

### 1. PR and worktree

```bash
gh pr view <pr> --json number,title,url,state,headRefName,baseRefName
git branch --show-current
```

Current branch equals `headRefName`: continue. Anything else: invoke `/soffner:dono <number>` with no task, continue inside the worktree it lands in. `ROOT="$(git rev-parse --show-toplevel)"`, `SHA="$(git rev-parse --short HEAD)"`.

### 2. Lock

As above. Nothing below runs without it.

### 3. Evidence folder

```bash
EVIDENCE="$ROOT/tmp/browser-test-auto/pr-<number>"
[ -d "$EVIDENCE" ] && mv "$EVIDENCE" "$EVIDENCE-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$EVIDENCE"
```

An old folder is moved aside so that no screenshot of a previous run ends up in this report.

### 4. Dispatch the runner

One Agent call: `subagent_type: "general-purpose"`, `model: "opus"`, a **fresh** agent, never `fork`. A fork inherits this conversation, and that is the bias the split exists to drop. The prompt is the template below with the inputs filled in and nothing added: no suspicion, no "this part already works", no hint about where to look. The operator's `focus` is the only steering, and it goes in their words.

```
You are the runner of the browser-test-auto skill. Read <SKILL_DIR>/SKILL.md in full and follow
the sections "What the invocation authorizes", "Settings", "Temporary user (V360)" and "Runner".
Nobody will answer a question: whatever you cannot do inside that contract becomes a blocked row
with its reason.

PR: #<number> <url>
Worktree: <ROOT> (sha <SHA>)
Evidence folder: <EVIDENCE> (absolute paths only)
Lock: held by the session that dispatched you. Do not touch it.
Operator focus (verbatim, may be empty): <focus>

Your last message is the full content of <EVIDENCE>/REPORT.md and nothing else.
```

`<SKILL_DIR>` is the base directory shown when this skill was loaded.

### 5. While the runner is in the field

No browser, no writes to the dev database, no edits under `$ROOT`. Work in other directories is fine. The runner's notification arrives on its own; do not poll it.

### 6. Audit

The runner's report is input, not a verdict. Read `REPORT.md`, then open **every** PNG it references in one batch (several `Read` calls in one message), and check each row against its own evidence:

- `pass` whose screenshot shows another screen, an empty shell, a modal over the content, or not the `Expected`: **disputed**.
- `pass` or `fail` without the evidence lines the [Runner](#r6-evidence) section requires: **disputed**.
- `fail` that the evidence shows: **confirmed**.

The audit only takes trust away. It never turns a `fail` into a `pass` and never settles a row from what you know about the code. Every disputed row goes back to the runner in **one** `SendMessage`, with the question per row. The runner rechecks in the browser, still under the lock, and answers with the new rows. Whatever is still disputed after that one round becomes `unverified: <why>` in the final report. The runner no longer reachable means the disputed rows go straight to `unverified`.

### 7. Close

1. Read `$EVIDENCE/settings.log`. Every `set` line needs a matching `restored` line. Missing (the runner died mid-run): restore each one yourself with the [Settings](#settings) recipe, still under the lock.
2. Release the lock.
3. Add the `Audit` table to `REPORT.md`, fix the `Map` counts, and print the report in the chat.

Nothing gets committed, nothing gets pushed, nothing is posted to the PR.

## Settings

A setting is the most common precondition, so the method is fixed.

Find the key in the code, never by guessing the name: grep the definition, not a usage, and cite its `file:line`. Then read, write and read back **in one command**, through the setter the project sanctions outside tests:

```
before = <read>
saved  = <write>
after  = <read again>
print before, saved, after
```

- **The documented setter is the only one.** In V360 that is `Vportal::Setting.set_setting!` in a `bin/rails runner` with `Vtenancy::Tenant.current = Vtenancy::Tenant.first` first. The bare `set_setting` raises outside tests. Never an admin screen: `/admin_panel` takes the dev server down, and a value changed through a screen leaves no `before`.
- **`saved` false, or `after` equal to `before`, means it did not happen.** A setter that ends in `save` rather than `save!` fails silently. Do not run the row as if it had.
- **Log before you write.** Append `set <group>.<name> before=<value>` to `$EVIDENCE/settings.log` *before* the write command, and `after=<value>` to the same line once it is proven. A run that dies halfway leaves the restore list on disk for the orchestrator.
- **The server lags behind the database.** Settings are cached per process. Reload once, then wait out the cache window. Never edit a file to force a reload: code is frozen.

Restore, at the end of the run: every `set` line back to its `before`, with the same one-command shape, then append `restored <group>.<name> value=<value>`. Only what this run changed, and only to what this run found. A setting that was already off its default belongs to someone else.

## Temporary user (V360)

The run signs in as a user that exists only for this PR, never as the operator. The operator's account carries staff permissions no customer has. And V360 keeps one session per user, so using it kicks the operator out of their own browser.

- **One user per PR, reused on re-runs:** username `teste_browser_pr<number>`, first name `TESTE_BROWSER`. An internal user's email has to match `Vportal::User.customer_email_regex`, which comes from the setting `general.customer_email_regex`: read it, do not guess the domain.
- **Least privilege.** The permissions are exactly the ones the delivered screens check (`can_do?(:<module>, :<permission>)` in the diff and in the controllers it touches). They go in a `TESTE_BROWSER_PR<number>` `Vportal::Roles::GlobalRole` inside a `TESTE_BROWSER_PR<number>` `Vportal::UserGroup` (`internal: true`), with the user as a member. When the PR adds a permission check, the map gets a row signed in as a second user, `teste_browser_pr<number>_noperm`, without it.
- **A fresh password on every run.** Random, meeting the complexity rule, provider `email`, saved with `save!(validate: false)` (the password-reuse validation refuses a legitimate save), proven with `valid_password?`. It lives only in the runner's context, long enough to type it into the form: never in a file, a log line or a screenshot.
- **First-access modals are database state.** Run the block under `### 3.3.1` of `.claude/skills/run-manual-tests/SKILL.md` in the worktree (V360 contract-tests it in `test/lib/run_manual_tests_first_access_runner_test.rb`) with this user's email, in the same runner. Its proof lines have to read `tutoriais pendentes=0` and `popups pendentes=0`. A modal that still shows up in a screenshot sends you back to this step. Hiding it through the DOM masks the only signal that the setup failed.
- A second factor on sign-in: turn it off on this user (the user is yours).

One runner creates or refreshes all of it and prints each proof: `valid_password?`, `can_do?` per permission, the two pending counts. Any proof false: fix it here, before Chrome opens.

**Sign-in.** In the run's tab, through the form. The email/password form can sit behind an expandable link ("Entrar Portal V360"). Confirm the signed-in user in the header before the first row. Cookies ignore the port, so the browser's `localhost` session now belongs to the temporary user on every port: the report says so, and the tab stays signed in for the operator to keep clicking as that user.

## Runner

### R1. Test map

```bash
gh pr view <number> --json body,commits --jq '.body, (.commits[] | .messageHeadline)'
gh pr diff <number>
```

One row per delivered behavior a user can reach: `| # | Behavior | Screen / route | Steps | Expected | Needs |`. Routes and views in the diff that the body does not mention still get a row. The body is what the author remembered; the diff is what shipped. Fill `Needs` by probing with reads (the setting's value, whether the data the screen lists exists), not by guessing. A row whose `Needs` falls outside the contract is `blocked: needs <action>` from the start. Write the map into `REPORT.md` before the first navigation.

### R2. Server

Only a server whose working directory is **this** worktree counts:

```bash
for pid in $(pgrep -f '^puma [0-9.]+ \(tcp://'); do
  if [ "$(readlink /proc/$pid/cwd)" = "$ROOT" ]; then tr '\0' ' ' < /proc/$pid/cmdline; echo; fi
done
```

The pattern is anchored so it does not match the shell running the loop. Found: reuse its port (`grep -oE 'tcp://[^)]+' | grep -oE '[0-9]+$'`). Not found: start the project's dev server from `$ROOT` in the background (V360: `bin/devq`), read the port it announces, wait for `Listening on`. Servers of other worktrees serve other commits and stay untouched.

Smoke test: `curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:<port>/"`. `200`/`302` is alive. `500` with `Migrations are pending` in the log: migrate per the contract. **`localhost`, never `127.0.0.1`**: the tenant is resolved from the host, and the IP gets the portal's 404 page on every route.

### R3. Temporary user and sign-in

As [Temporary user](#temporary-user-v360).

### R4. Chrome

Load the tools in one `ToolSearch` call: `tabs_context_mcp`, `tabs_create_mcp`, `tabs_close_mcp`, `navigate`, `computer`, `read_page`, `find`, `form_input`, `read_console_messages`, `read_network_requests`.

One tab for the whole run, settled before the first navigation. `tabs_context_mcp` with `createIfEmpty: true` already opens an empty tab in the group: that is `TAB`. Only when the group already had tabs does `tabs_create_mcp` run, once. Every later call carries `tabId: TAB`, `navigate` included. A `navigate` without it drives the group's first tab, not yours. Tabs outside the group belong to the operator and are never touched. Desktop viewport only.

### R5. Running the map

For each row, in order:

1. Note `wc -l < "$ROOT/log/development.log"`.
2. `navigate`, do the steps as a user would, locating elements with `read_page` and `find`.
3. Confirm `Expected` from `read_page`, not from a hunch about the screenshot.
4. `read_console_messages` with `onlyErrors: true`. A JS error is a finding when the erroring asset is in the diff, even on a screen the PR did not list; otherwise a Note.
5. `tail -n +<line> "$ROOT/log/development.log" | grep -nE 'Completed 5[0-9]{2}|Error|Exception'`.
6. Mark `pass`, `fail` or `blocked`. A row that cannot run because an earlier one failed is `blocked: upstream fail #<n>`.

A `fail` is reproduced once, with fresh navigation, before it counts. Seen once and not again is `flaky, seen once`. The suspected cause of a `fail` is confirmed by reading the code (`file:line`) or written as `not located`. A bug is a finding, never a fix.

### R6. Evidence

- One screenshot per row at least (`computer` `screenshot` with `save_to_disk: true`, copied to `$EVIDENCE/<nn>-<row-slug>.png`), plus one per finding showing the broken state.
- Per row in `REPORT.md`, the lines the orchestrator audits with: the steps done, `Expected` against what `read_page` showed, console errors verbatim or `none`, server log hits verbatim or `none`, and any write request seen on a pre-existing record. A claim without these lines gets disputed.
- No credential, token or password in any file under `$EVIDENCE`.

### R7. Before the last message

Restore every setting in `settings.log` ([Settings](#settings)). Leave the server running (its pid and port go in the report), the tab open and signed in, and every `TESTE_` record in place, all listed. Then send `REPORT.md` as the last message.

## Report

Fixed shape, in `REPORT.md` and in the chat:

```
## browser-test-auto: PR #<number> <title>

Environment: <worktree>, <sha>, http://localhost:<port>, server <reused | started, pid N>, Chrome tab <TAB>, signed in as <temp user email>
Map: <n> rows, <p> pass, <f> fail, <b> blocked, <u> unverified
Lock: <acquired at, released at; stale lock taken over from <owner> when it happened>

### Findings
| # | Row | What happens | Evidence | Suspected cause |

### Passed
| # | Behavior | Evidence |

### Blocked
| # | Row | Reason |

### Audit
| # | Runner said | Evidence shows | Outcome |
(confirmed | rechecked: <new status> | unverified: <why>)

### Records created
| Model | id | Name |
(temp users, role and group included; left in place for the environment owner)

### Settings changed
| Group.name | Before | After | Restored |

### Migrations applied
| Version |

### Notes
(console errors on untouched screens, the localhost session now being the temp user's, anything else that is not a verdict on the PR)
```

## Rationalizations that mean stop

| Thought | Reality |
|---------|---------|
| "A fork is simpler, it already knows the PR" | It also knows what the implementer believes. Fresh agent, template inputs only. |
| "The runner said pass, I will copy the row" | Open the PNG. A pass with a screenshot of an empty shell is the failure the audit exists for. |
| "That fail is wrong, the code clearly works" | The audit never flips a fail. Send it back with the question, or it stays as the runner saw it. |
| "The lock is hours old, whoever holds it forgot" | A live pid may be mid-row. Wait, or stop with the owner line so the operator can decide. |
| "I will ask the operator, it is quicker" | Nobody is there. Outside the contract is a blocked row, and the list of blocked rows is part of the deliverable. |
| "The operator's account is already signed in" | Staff permissions, and one session per user. Temporary user. |
| "The modal is in the way, I will close it in the DOM" | Back to the first-access step. The modal is the proof it failed. |
| "The next run needs this setting too, I will leave it" | Restore it. The next run sets it again under its own lock. |
| "The fix is one line" | Code is frozen while the map runs. Report it. |
| "127.0.0.1 is the same as localhost" | The tenant comes from the host. |

## When NOT to use

- Someone at the keyboard who wants to be asked before each write, or who wants to keep driving the run: `/soffner:browser-test`.
- API or token flows with no screen, and mobile layouts: this skill drives one desktop tab.
- Recording a demo: `/soffner:demo`.
