---
name: evolve
description: Use ONLY when the user explicitly invokes `/evolve`, or asks for an evolve round by name. Never auto-trigger from words like improve, evolve or polish. Continuous product evolution when nobody has a direction in mind - surveys the screens, code and features of a scope (or picks the scope itself), sends scouts with different lenses to propose evidence-backed changes, has a panel of independent judge subagents kill the weak ones, prototypes the survivors as before and after pictures of the real product (they look real and need not work), has fresh judges check the pictures, and puts the best, at most five, on a choose page to pick from. Keeps a ledger across runs, so a declined idea never comes back and the operator's picks become the direction.
---

# evolve

```
/evolve [scope] [-- hint]
```

| Argument | Read as |
|---|---|
| `scope` (optional) | a screen, flow, feature, path or module, named the way the team names it. Absent: the run picks one ([step 1](#1-ledger-and-scope)). |
| `hint` (optional, after `--`) | free text the scouts and judges get ("menos cliques", "foco no gestor"). It reorders the ranking; it never lets in a proposal without evidence. |

A round of product evolution for when there is no roadmap item to build. The run looks at what exists, proposes changes it can show, throws most of them away, and puts the survivors in front of the operator as before and after pictures on a [choose](../choose/SKILL.md) page. The picks go into a ledger, and the ledger is the direction the next runs follow.

**The run is a funnel and it always ends.** At most twenty candidates, six prototyped, five on the page, one fix pass per picture, two rounds of the page. Nothing surviving is a valid result: report what was checked and show no page. It never invents work to fill the page.

## What the invocation authorizes

Inside the checkout this run claims (a devslot slot, or a throwaway worktree), with no question asked: running the product, migrations, a temporary user, records with the `TESTE_` prefix, throwaway code edits for prototypes, and deleting all of it at the end. Outside it, writing in `~/Documents/evolve/<repo>/`. Nothing else: no commit, no push, no PR, no message to anyone, nothing in the main worktree or another slot. Building a chosen proposal is a separate request.

## Where things go

`<SKILL_DIR>` is the base directory shown when this skill was loaded. `<repo>` is the main worktree's folder name, `basename "$(git worktree list --porcelain | sed -n '1s/^worktree //p')"`. Shell variables do not persist between Bash calls: write the paths in full.

| What | Where |
|---|---|
| The ledger, one per product | `~/Documents/evolve/<repo>/ledger.md` |
| This run: survey, slate, verdicts, prototype scripts and patches, the page's spec and the page | `RUN=~/Documents/evolve/<repo>/<YYYY-MM-DD>` (`-2`, `-3` for a second run that day) |
| The temporary user's session | `<checkout>/tmp/evolve/auth.json`, gone at teardown |

Pictures are taken with demo's recorder, `<SKILL_DIR>/../demo/demo-take.js rehearse` (installed as `<SKILL_DIR>/../demo/SKILL.md` step 4 says when `~/.cache/soffner-demo/node_modules/playwright` is missing), always at `VIEWPORT=1440x900` so that every picture of a run has one size. A shot file exports `async setup(page)` and `async take(page)` (both required, either may be empty), and each one leaves `<shot>.png` and `<shot>.aria.txt` beside it. Every `rehearse` is its own isolated headless Chrome, so subagents run it at the same time without touching each other or the operator's browser.

## 1. Ledger and scope

Read the ledger first. Its states decide what this run may offer:

- `chosen` and `built`: never offered again. A `chosen` that the base branch's `git log` shows built since becomes `built <sha>`.
- `declined` (the operator kept today) and `killed` (a judge cut it): offered again only with evidence the entry did not have, and the group's `help` then says what is new.
- `asked`: a question or a request the operator left. Answer it this run when the scope matches.
- Every note, in any state, is the closest thing to a direction the operator has given. Scouts and judges get them verbatim.

Every run appends its heading to the ledger, the empty ones too, and every candidate a cut took out goes under it as one line, `- killed: <title> · <why, one clause>`. Without that, the rotation keeps landing on the same dead scope and the scouts keep bringing back the same weak ideas.

With no scope given, list the product's areas from its own navigation (the menu, the top-level routes, or the modules of a product without a UI) and take the one the ledger visited least recently, breaking ties by recent activity (`git log --since=60.days --name-only` on its paths). Never the previous run's scope, a run that ended empty included, unless it has `asked` entries. The first line to the operator says which scope and why.

## 2. The checkout and the product running

Read the main worktree's `CLAUDE.md` and `AGENTS.md`. Of `.claude/rules/`, grep the `description:` lines and read only the screenshot or print rules and `devslot.md`: the rest is about writing code, which this run does not do. A screenshot rule (the deck has `.claude/rules/prints.md`) decides how every picture of the run is made, and beats everything below. `<base>` is the integration branch `CLAUDE.md` names, else the default branch: the run looks at the product as it is there, not at anyone's work in progress.

- **With `bin/devslot`** (found the way `<SKILL_DIR>/../demo/SKILL.md` step 1 finds it): `"$DEVSLOT" claim evolve-<date> evolve-<date> <base>`, enter the slot with `EnterWorktree`, and follow its rule (`.claude/rules/devslot.md`): migrate, start the server, base URL `http://devslot<N>.localhost:<port>`. Sign in as demo's step 4 does, with `teste_evolve` as the username, `TESTE_EVOLVE` for its role and group, `<checkout>/tmp/evolve` as its work folder, and the permissions the scope's screens check (what a customer in that role sees, never staff). The session goes to `<checkout>/tmp/evolve/auth.json`.
- **Without it**: a throwaway worktree, `git fetch origin <base> && git worktree add -b evolve-<date> .claude/worktrees/evolve-<date> origin/<base>`, with the product run the way the project documents, on a port of its own. When it has a sign-in, save a signed-in session to `<checkout>/tmp/evolve/auth.json` with `SAVE_STORAGE`, as the last command of demo's step 4 does, as a user the project's seeds or docs provide. No migrations, users or records unless the worktree has a database of its own: without one, the database is the main worktree's, and the survey uses the data that is there.
- **No UI** (a CLI, an API, a library): no server, and no pictures: today and the proposal are `code` blocks of what the person sees (the command's output, the response, the call).

## 3. Survey

Before anyone proposes anything, the lead takes the inventory every later step works from:

- **One shot per screen of the scope**, in the state a user normally finds it, plus its empty, error and long-list states when they exist: `$RUN/survey/<n>-<slug>.js`, a `setup` that opens the screen and waits for its content, and an empty `take`. One `rehearse` call takes them all. Open every PNG: a sign-in page or a first-access modal sends you back to step 2, once. The second time, stop, teardown, and report what is still on screen.
- **Data a state needs** (a long list, a filled form): create it in the checkout's database, `TESTE_` prefixed, when step 2 allows writing there.
- **`$RUN/survey.md`**: for each screen, its picture, its route, the files that render it (controller, view, component) and the models behind it; then the scope's `git log --oneline -30`, its `TODO` and `FIXME`, and the open issues that mention it (`gh issue list --search`).

## 4. Scouts

Four `general-purpose` subagents, in parallel in one message, one per lens, each given the template below. Each returns at most five candidates.

| Lens | Looks for |
|---|---|
| `journey` | the person doing the scope's main jobs, step by step, in the running product: extra steps, dead ends, no feedback after an action, the moment they leave for a spreadsheet or Slack. It clicks through with its own shots. |
| `latent` | what the code knows or can do that the screens hide or make hard: columns and associations never shown, endpoints with no screen, a half-built feature behind a flag, a `TODO` with a reason. |
| `coherence` | the product against itself: one job done three ways on three screens, the best screen of the product as the yardstick for the scope's worst. |
| `bet` | one or two moves that change what the scope can do for its person, each built on an asset the product already has (data, a model, an integration, a job). |

```
You are a scout looking for ways to evolve <product>'s <scope>, through one lens: <lens>, which
means <its line from the table>. Nobody gave a direction; a proposal is worth what its evidence
is worth.

Read <RUN>/survey.md and open its pictures. The code is in <checkout>; read it freely. To see a
screen or a step the survey lacks: <for a running web product: write shot files in
<RUN>/scout-<lens>/ (each exports async setup(page) and async take(page); goto takes paths) and run
  cd <RUN>/scout-<lens> && BASE_URL=<base url> STORAGE=<auth.json> VIEWPORT=1440x900 \
    node <recorder> rehearse <files in order>
each leaving a PNG and an accessibility tree; otherwise, the project's own picture command>.
Change nothing in the repository. Records you need, create with the TESTE_ prefix; leave the
survey's as they are.

From the ledger, as written there:
- chosen or built, never again: <titles>
- declined or killed, only with evidence the entry did not have, and say what is new: <titles, why, notes>
- asked, answer these when they fall in this scope: <entries>
The operator's notes are taste, not orders. This run's hint: <hint, or none>

Rules:
- Evidence is something that exists now: a file:line, a picture and what it shows, a commit, a
  TODO, an issue. No evidence, no candidate.
- Out, unless your evidence is specific to this product: a dashboard, dark mode, generic search,
  an AI chat, a notifications center, an onboarding tour, "a modern look".
- Taste is not a candidate. A candidate changes what the person can do, how fast, or how sure
  they are of what they see.
- Concrete: say what appears, moves or disappears, and on which screen.

Return up to five, best first, each exactly:

### <title, a few words>
- screen: <route> (picture: <path>)
- evidence: <what exists now, with its location>
- today: <what the person does now, one sentence>
- after: <what changes on screen>
- gain: <who gains, and what changes in their day>
- data: <where everything the after shows comes from: model, column, endpoint; or "new: <what>">
- size: S | M | L
```

## 5. First cut: the panel

Number the candidates `C1`, `C2`..., merge duplicates (keeping the evidence of both), drop what the ledger has as `chosen` or `built`, and what it has as `declined` or `killed` unless the candidate names evidence the entry lacked, and write the slate to `$RUN/slate.md`.

Then three `general-purpose` judges, fresh and in parallel, each with the whole slate and the survey. Never the scouts' reasoning, nor which scout wrote what, nor your own preference.

| Judge | Kills a candidate when |
|---|---|
| `person` | the person would not notice the gain, it adds a step or noise to the common path, or the evidence does not show they have the problem |
| `engineer` | the data is not there and the size hides it, it already exists elsewhere in the product, it breaks a permission, a flow or a convention, or it undoes a deliberate decision (`git log -S`, `git blame` on the lines) without answering its reason |
| `critic` | it would be proposed for any product, it is taste, it is a ledger idea in new words, or it is not worth the operator's minute next to the rest of the slate |

```
You are the <judge> on a panel deciding which proposed changes to <product>'s <scope> are worth
prototyping. You did not write them and you owe them nothing. Agents judging generated proposals
tend to approve them; correct for that. When unsure, kill.

The slate: <RUN>/slate.md. Today's screens: <RUN>/survey.md and its pictures. The code is in
<checkout>: check every claim you rely on (open the file:line, find the column, run the git log).
Change nothing.

You kill a candidate when <the judge's row>.
The ledger, titles, states and notes: <its entries>. This run's hint: <hint, or none>.

For each candidate: keep or kill, why, and what you checked. Then rank the ones you kept, best
first, by the gain for the person over the size.

End with only this JSON:
{"verdicts": [{"id": "C1", "verdict": "keep", "why": "...", "checked": "..."}], "ranking": ["C4", "C1"]}
```

Then the cut, mechanically:

- **Out** when two judges kill it, or when one judge's kill rests on a fact you check and confirm (the data is not there, it already exists, the decision was deliberate).
- **Rank** the rest by the sum of their places in the three rankings, a judge that killed it counting it at place N+1, N being the number of candidates on the slate. Ties go to the smaller size, then to the hint.
- **Keep the top six**, at most two per screen and at most two of size L. You may still kill a survivor; you never bring one back.
- **A second variant** of a survivor is built only when a judge or its scout named a fork the operator should decide (where it goes, how much of it), never by default, and never more than two in the run.

Write the verdicts and the cut to `$RUN/cut-1.md`. Nothing survived: write the ledger (the heading, `nothing survived`, and the killed lines), tell the operator what was checked and how each candidate died, then teardown.

## 6. Prototypes

The before is today's screen; the after is the same screen with the proposal applied. **It has to look real; it does not have to work.** Same record, same scroll, same state in both, so that the only difference between the two pictures is the proposal.

- **A web screen** (the default): a DOM patch over the real page, so the page, its data and its styles are the product's and only the proposal's piece is injected. One `general-purpose` subagent per survivor, in parallel, with the template below.
- **Deeper than markup** (a new screen or route, or a project whose pictures come from its own pipeline, as in the deck): a code prototype in the checkout, by the lead, one at a time. Hardcoded data is fine. Render it, take the after, `git diff > $RUN/proto/<C>.patch`, then `git checkout -- . && git clean -fd` before the next.
- **Nothing on screen**: today and the proposal as `code` blocks.

```
You build the before and after pictures of one proposed change to <product>. They are prototypes:
the after only has to look like the change was made. Nothing in it has to work.

The proposal: <its block from the slate>
Today's screen: <its survey shot>, <its PNG> and its accessibility tree <its aria.txt>.

In <RUN>/proto/ write <C>-before.js and <C>-after.js. Both take the survey shot's setup, then wait
for the element the proposal is about. <C>-before.js has an empty take. <C>-after.js's take changes
the page with page.evaluate: insert, move, hide or restyle what the proposal changes, and nothing
else. Build the new parts from the product's own markup: find a screen that already has that kind
of element (grep the views and components), and reuse its HTML and classes, so the after looks
like the product and not like a mockup. Values on screen are the page's own data, or plausible
values for this record; never real customer data brought from elsewhere.

Run
  cd <RUN>/proto && BASE_URL=<base url> STORAGE=<auth.json> VIEWPORT=1440x900 \
    node <recorder> rehearse <C>-before.js <C>-after.js
and open both PNGs. Fix and run again until the before shows today and the after shows the
proposal, at most four runs.

Return the two PNG paths, one line on what the after shows, and what in it is illustrative (data
or behavior the product does not have yet). Change nothing in the repository.
```

Open every pair yourself before it reaches the judges: a pair that does not show its proposal you fix once, or it is out.

## 7. Second cut: the pictures

Two fresh `general-purpose` judges, in parallel, with every pair, its block from the slate and its builder's illustrative line, never the first cut's verdicts:

| Judge | Looks at |
|---|---|
| `person` | at a glance, is the after better for the job than the before? What got worse: something lost, pushed down, crowded? |
| `designer` | does the after look like the product (its components, spacing, type, colors)? Does it show the proposal and only it, with no restyle on the side? Does anything look real that is not, beyond what its illustrative line declares? |

```
You are the <judge> looking at prototypes of proposed changes to <product>'s <scope>. Each comes as
two pictures of the same screen: before is today, after is the proposal applied. The after is a
prototype, so judge what it shows, not whether it works. You did not make them and you owe them
nothing. When unsure, kill.

The proposals: <their blocks from the slate, each with the line saying what in its after is
illustrative>. The pictures: <RUN>/proto/<C>-before.png and <C>-after.png, or for a product with
no UI the two code blocks. Open every one.

You look at: <the judge's row>.

For each proposal: keep; fix, with the one change to the after that would make you keep it; or
kill, naming what in the pictures shows it.

End with only this JSON:
{"verdicts": [{"id": "C4", "verdict": "fix", "why": "...", "fix": "..."}]}
```

A `kill` from either judge is out. A `fix` you apply yourself, in one pass, to `<C>-after.js` (both judges asking: both, or the `person`'s when they conflict), and check the new picture against the instruction; there is no third judging. Keep at most five, in the first cut's order, and write `$RUN/cut-2.md`. None left: the same exit as the first cut.

## 8. The page

Build it with `<SKILL_DIR>/../choose/build.py`, following `<SKILL_DIR>/../choose/SKILL.md` steps 4 and 5 (check what it copies, then open it in the operator's browser). The page is in the operator's language, as choose says. The spec, the pictures it points at and the page stay in `$RUN`; the page is `$RUN/round-<n>.html`, its `store` is `evolve-<repo>-<basename of $RUN>-<n>`, so a second run on the same day never opens with the first one's picks.

One group per proposal, `kind: one`, its `help` the gain and the evidence:

| Option | Is |
|---|---|
| `<G>1` | "Como está hoje", `chosen`, no picture; `what` says what today does wrong, from the evidence |
| `<G>2`, and `<G>3` for a second variant | the proposal: `before` and `image` (the after), `what` (what changes), `source` (where the data comes from, then "Protótipo: só a aparência" and what is illustrative), `tag` (`esforço pequeno`, `médio` or `grande`), `tone` |

Leaving a group alone keeps today, so silence is a no. With no UI, `<G>1` carries today's `code` and `<G>2` the proposal's, with no `before`.

Append the run's heading and its killed lines to the ledger now, so they are there even if no answer comes. Then [teardown](#10-teardown): the pictures, scripts and patches are in `$RUN`, and a second round claims again. Tell the operator in a few lines: the scope and why, how many candidates each cut took out, one line per proposal on the page, and that the button copies the choices to paste in the chat. Then wait.

## 9. The answer

Read it as choose step 6 says, then write the ledger before anything else:

| The answer | State |
|---|---|
| `<G>2` or `<G>3` chosen | `chosen`, with its notes |
| `<G>1` kept | `declined`, with its note when it has one: why not is the best taste signal the next runs get |
| a note, on any option, asking for a change | a second round for those proposals only: claim again (step 2), recreate the data their survey shots need, take both before and after again with the note as a constraint, check each pair against its note yourself in place of the second cut, and a new page with new letters and a new `store`. What the second round still leaves open is `asked` |
| `Mais` with a new idea | `asked`, for a later run. It never starts a third round. |

An entry, appended under the run's heading:

```markdown
## <date> · <scope> (<given | rotation>) · round <n> · <RUN>/round-<n>.html

### A · <title> · chosen A2
- screen: <route> · size: S
- evidence: <...>
- after: <...>
- data: <...>
- notes: <verbatim, or none>
- pictures: <RUN>/proto/C4-before.png, <RUN>/proto/C4-after.png · prototype: <RUN>/proto/C4-after.js
- state: chosen
```

Then print each chosen proposal's entry, the brief whoever builds it starts from. Building is a separate request, and the prototype is a picture of the goal, never code to ship.

## 10. Teardown

After the page is built, and on every way out once the checkout exists:

- **A slot**: `rm -rf <slot>/tmp/evolve` (the temporary user's live session), then the command in `<SKILL_DIR>/../demo/SKILL.md` step 9 with `evolve-<date>` as the branch: reset, clean, detach, delete the branch, `release`. Then `ExitWorktree` with `keep`.
- **A throwaway worktree**: stop the server, `git worktree remove --force .claude/worktrees/evolve-<date>`, `git branch -D evolve-<date>`.

`release` refusing: say so in the report, with the slot still held.

## Never

- Never prototype a candidate the first cut did not keep, nor put on the page a picture the second cut did not see (a second round's pictures are checked against the note instead).
- Never show the after on other data, size or state than the before.
- Never pass a prototype off as the product: its `source` says what is illustrative.
- Never offer a `declined` idea again without naming the new evidence.
- Never real customer data, a token or a secret in a picture. The page and the ledger stay on the operator's machine.
- Never edit, commit or push in the main worktree or anyone's branch.
