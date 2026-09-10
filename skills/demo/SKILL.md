---
name: demo
description: Use when the user asks for a demo video of a pull request (record a demo, film the PR, put a video on the PR). Plans a shot list from what the PR delivers, reuses or starts the dev server of the PR's worktree, films the route in the recording Chrome with aditor, and writes a "### Demo" section into the PR body with the video and a short pt-BR text explaining what it shows. Never opens a browser, a server or a PR edit on its own initiative.
---

# demo

Turn a pull request into a short film a reviewer can watch instead of checking it out. Same
discipline as `/soffner:browser-test`, different deliverable: that one proves the PR works and
reports findings, this one shows the PR working and publishes the result on the PR.

**The invocation authorizes the recording browser, the dev server of this worktree and one edit to
the PR body.** It does not authorize a comment, a review, a commit, a push, or any write to the
database beyond what a user of the feature does through the screen.

A demo is a **happy path**. If the route hits a bug, the take stops and the bug is reported. Do
not film around it, and do not fix it: fixing is a separate request, and Rails reloads under the
remaining shots anyway.

## Arguments

`/demo [pr] [what to show]`

| Token | Rule |
|-------|------|
| `pr` (optional) | `123`, `#123`, a URL or a branch. Missing: the PR of the current branch. No PR there either: ask and stop. |
| `what to show` (optional) | Free text narrowing the route to one behavior. Missing: the route covers what the PR body and the diff deliver. |

## Flow

1. PR, worktree and the state already on the machine.
2. Shot list.
3. Server.
4. Recording browser.
5. Film, shot by shot.
6. Cut it down.
7. Attach and publish the `### Demo` section.
8. Ask what to tear down.

### 1. PR, worktree and what is already running

```bash
gh pr view <pr> --json number,title,url,state,headRefName,baseRefName,isDraft
git branch --show-current && git rev-parse --short HEAD
```

Current branch is not `headRefName`: invoke `/soffner:dono <number>` with no task to land in the
PR's worktree, then continue from step 2 inside it. Never film a PR from another branch's
checkout. The SHA goes in the demo text, because the film shows that commit and no other.

**Assume something is already up.** This is normally run right after `/soffner:browser-test`, which
leaves the server running, the browser signed in and the preconditions in place on purpose. Check
before starting anything, and reuse what answers:

```bash
ROOT="$(git rev-parse --show-toplevel)"
for pid in $(pgrep -f '^puma [0-9.]+ \(tcp://'); do
  [ "$(readlink /proc/$pid/cwd)" = "$ROOT" ] && tr '\0' ' ' < /proc/$pid/cmdline && echo
done
curl -sf --max-time 2 http://127.0.0.1:9222/json/version >/dev/null && echo "recording chrome up"
```

Anything reused gets said in the report, so the reader knows the film came from a server and a
session this run did not build.

### 2. Shot list

Read the delivery before planning the route:

```bash
gh pr view <number> --json body,commits --jq '.body, (.commits[] | .messageHeadline)'
gh pr diff <number>
```

A demo is not the test map. The map covers every delivered behavior; the shot list covers the
**two to five** that a reviewer needs to see, in the order that tells the story. Prefer the shot
that shows a difference (before state, action, after state) over the shot that shows a screen.

```
| # | Shot | Route | Actions | What it proves | Seconds |
```

Rules for the route:

- **Start from a stable screen**, never mid-flow. The first frame is the thumbnail.
- **One idea per shot.** A shot that needs two sentences to explain is two shots.
- **Preconditions come before the camera rolls**, never during. Data the shot needs, created with
  the `TESTE_` prefix, exists before the take. Nobody wants to watch a form being filled with
  setup data.
- **Total under 60 seconds.** Longer than that and reviewers scrub instead of watching.
- Anything the route needs that is not "a user clicking the feature" (a setting that is not the
  PR's own flag, a write outside the browser, a change to a pre-existing record) is the same gate
  `/soffner:browser-test` applies. Ask before, one question, and mark the shot dropped if the
  answer is no.

Print the shot list before filming. It is information, not a gate, but it is also the last cheap
moment to change the route.

### 3. Server

Reuse the one found in step 1. None found: start the project's dev server in the background from `$ROOT`, read the port it
announces, wait for `Listening on`.

```bash
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:<port>/"
```

`200` or `302` and the server is fine. `localhost`, never `127.0.0.1`: an app that resolves the account from the
hostname does not recognise the literal IP and answers its own 404 on every route, which on film
looks like a broken feature. A `500` with pending migrations is a gate, not a chore.

### 4. Recording browser

The film comes from the recording Chrome, not the everyday one. Bring it up and pick the tab
exactly as `/soffner:browser-record` describes, and read that skill's first two sections before
rolling: what the frames do and do not contain decides how the route has to be driven.

Two properties of the capture change the direction:

- **The cursor is not in the frames.** Every click is invisible, so the film needs the page's own
  feedback (focus ring, spinner, flash message, row appearing) to carry each beat. A shot whose
  only evidence is "the cursor moved there" cannot be filmed; add a caption in step 6 instead.
- **The frame size is fixed at the first frame.** Size the window before rolling and leave it
  alone. No DevTools, no resize, no zoom during a take.

To drive the page with Claude in Chrome rather than by hand, the recording instance has to be the
selected browser: `list_connected_browsers`, then the mandatory `AskUserQuestion` listing every
connected browser, then `select_browser`. Never pick one silently. The instance not on the list
means driving it by hand, which is fine and worth one line in the report.

### 5. Film

**One take per shot**, into the evidence folder, never one long take for the whole route. A
fumbled step then costs one retake instead of the film.

```bash
EVIDENCE="$ROOT/tmp/demo/pr-<number>"; mkdir -p "$EVIDENCE"
REC=$(aditor record --tab "$TAB" --cdp-port 9222 -o "$EVIDENCE/<n>-<slug>.mp4" --yes --json \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
# run the shot
aditor stop "$REC" --json
```

Between shots: land on the next starting screen **before** the next `record` call, so no take opens
on a loading page.

After each take, read `duration` and `size_bytes` from `stop`. A duration far under the wall clock,
or a handful of kilobytes for a busy screen, is a dropped take. Redo it before moving on, because
a missing shot is only discovered at stitch time otherwise.

A shot that fails for a reason in the product is a **finding**, not a retake. Stop filming, report
it, and let the user decide whether the PR still deserves a demo.

### 6. Cut it down

The raw takes are longer and slower than anyone wants. Post-production is the same tool:

Every editing subcommand takes the input as a **positional** argument, writes to `-o`, and needs
`--yes` to overwrite. Trim each take first, then caption it, then stitch:

```bash
aditor cut --from 0:02 --to 0:11 -o 1-cut.mp4 --yes 1-raw.mp4
aditor write --text "Filtro salvo pelo usuário" --from 0 --to 3 \
             --x 40 --y 40 --font-size 42 --color 'white@0.9' -o 1-titled.mp4 --yes 1-cut.mp4
aditor speed -x 1.5 -o 1-final.mp4 --yes 1-titled.mp4
```

`write` without `--from/--to` (or `--frame`) burns the caption over the whole take, which is
almost never what a shot wants.

**Stitching is not a concat command.** `append --at <seconds> <BASE> <INSERT>` inserts one file
into another, and `--at` equal to the base's duration is what makes it an append. So the shots
chain one at a time, reading the running duration back between steps, and never writing over the
file being read:

```bash
cp 1-final.mp4 demo.mp4
for shot in 2-final.mp4 3-final.mp4; do
  END=$(aditor info demo.mp4 --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["format"]["duration"])')
  aditor append --at "$END" demo.mp4 "$shot" -o demo-next.mp4 --yes && mv demo-next.mp4 demo.mp4
done
aditor info demo.mp4
```

`append` re-encodes and scales each insert to the **first** file's dimensions, so a shot filmed
at another window size comes back letterboxed instead of rejected. Same window for every take, or
the film has black bars in the middle.

Every shot gets a caption, because the cursor is not in the frames and the reviewer has no idea
what was clicked. Captions are pt-BR: they are published to a pt-BR audience.

Two hard targets before the file leaves this step:

| Target | Why |
|--------|-----|
| Under 60 seconds | A reviewer watches a minute and scrubs anything longer |
| Under 10 MB | The browser upload tool rejects more, which is stricter than GitHub's own cap |

Over 10 MB: re-encode instead of cutting content, `aditor convert --crf 28 -o small.mp4 --yes demo.mp4`,
then `aditor info` again. Still over: the route was too long, and the fix is fewer shots.

### 7. Attach and publish

GitHub has no API for attaching a video. The file becomes a URL only by going through an upload
box in the browser, so that is the one step that happens on the page.

1. Open the PR in the recording Chrome and `find` the file input of the comment box at the bottom
   (`input[type=file]`). The comment box is used as an uploader and **nothing is ever submitted
   from it**.
2. `file_upload` with the absolute path of `demo.mp4` and that input's ref.
3. Read the markdown GitHub writes into the textarea. It carries the permanent asset URL
   (`https://github.com/user-attachments/assets/<uuid>`). That URL is the deliverable of this step.
4. Clear the textarea. Leaving a draft is untidy; submitting it is a comment nobody asked for.

`file_upload` rejects a path outside the folders shared with this session. When it does, do not
hunt for a workaround: ask the user, in one question, to drop `demo.mp4` into the PR comment box
themselves and paste back the URL GitHub generates. State the absolute path in the question. One
manual drag beats a broken publish.

Then write the section into the **body**, with `gh api`, never `gh pr edit`, which exits 1 without
applying anything on this account:

```bash
gh api "repos/{owner}/{repo}/pulls/<number>" --jq .body > /tmp/pr-body.md
# edit /tmp/pr-body.md, then
gh api -X PATCH "repos/{owner}/{repo}/pulls/<number>" -F body=@/tmp/pr-body.md
gh api "repos/{owner}/{repo}/pulls/<number>" --jq .body | head -40
```

Read the body back every time. A silent no-op looks exactly like a success.

Where the section goes, and what it looks like:

- **Replace, never append.** A `### Demo` section already in the body is this skill's own previous
  run: swap its contents, so a second demo does not stack two videos.
- **Before the ISO 42001 block.** When the body carries `<!-- iso42001:start -->`, the section goes
  immediately above it, since that block is a signed record that ends the body. No marker: at the end.
- **Everything else in the body is untouched.** The template sections, the test plan and the
  screenshots belong to the author.

```markdown
### Demo

https://github.com/user-attachments/assets/<uuid>

<uma a três frases em pt-BR: o que o vídeo mostra, na ordem em que aparece, e o que o revisor
deve reparar. Sem passo a passo, sem "clique aqui". Feche com o commit filmado.>

<!-- Gravado em <sha> -->
```

Three rules on that text, which is pt-BR because it is published to a pt-BR team:

- **It describes the film, not the feature.** The PR body already explains the feature. This says
  what passes on screen, so the reviewer knows what they are looking at.
- **It names what is invisible.** The cursor is not in the frames, so any click the captions did
  not cover gets a clause here.
- **It ends on the commit.** The film ages the moment someone pushes, and the SHA is what tells
  a reader whether it still describes the PR.

The bare URL on its own line is what makes GitHub render a player. Wrapping it in markdown link
syntax or an `<img>` tag gives a dead link instead.

### 8. Teardown

One `AskUserQuestion`, offering only what this run started:

| Offer | When |
|-------|------|
| The dev server | only if this run started it. `Keep it on <port>` first |
| The recording Chrome | always. `Keep it open` first, since a retake is the usual next step |
| The raw takes in `$EVIDENCE` | `Keep them` first. They are the only way to re-cut without refilming |

A server or a browser this run found already up is never offered: it belongs to whoever started
it. Unanswered means everything stays, and the report says so.

## Report

```
## demo: PR #<number> <title>

Environment: <worktree>, <sha>, http://localhost:<port> (<started|reused>), Chrome <up|reused>
Shots: <n> filmed, <n> retaken, <n> dropped
File: <path> (<duration>s, <WxH>, <size>)
Published: <asset url> in the PR body, section ### Demo
Gates asked: <action, target, answer>
Findings: <bugs that stopped a shot, or none>
Left behind: <server, browser, raw takes, TESTE_ records>
```

## Rationalizations that mean stop

| Thought | Reality |
|---------|---------|
| "The shot broke, I will fix the bug and refilm" | A bug that stops a shot is a finding. Fixing reloads the app under the remaining shots and the film stops matching the PR. |
| "One long take is simpler than stitching" | One fumble costs the whole film. One take per shot, stitched with `append`. |
| "I will set the data up on camera" | Preconditions before the camera rolls. Nobody watches a form being filled with setup. |
| "It is 3 minutes but it is all relevant" | Under 60 seconds. Relevance is what the shot list is for. |
| "I will paste the video URL as a markdown link" | Only a bare URL on its own line renders a player. |
| "`gh pr edit --body` is the obvious way" | It exits 1 without applying on this account. `gh api -X PATCH`, then read the body back. |
| "I will append the Demo section, the old one is further up" | Replace it. Two players in one body is this skill running twice. |
| "The body has a weird HTML comment block at the end, I will drop it" | That is the ISO 42001 record. The section goes above it and the block stays. |
| "I will submit the comment, the video is in it anyway" | The comment box is an uploader. The deliverable is the body. |
| "The everyday Chrome is already signed in, I will film there" | It has no debug port and never will. Only the recording instance has tab ids on 9222. |
| "browser-test left a server on another worktree's port, close enough" | Another worktree is another commit. Detect by cwd. |

## When NOT to use

- Proving the PR works, with findings and evidence: `/soffner:browser-test`.
- A video with no PR to publish it on: `/soffner:browser-record`.
- Still screenshots for the PR body: take them in `/soffner:browser-test` and attach them the same way step 7 describes.
- The PR is not open yet: open it first, since the section is written into its body.
