---
name: demo
description: Use when the user asks for a demo video of a pull request (record a demo, film the PR, put a video on the PR). Plans a shot list from what the PR delivers, reuses or starts the dev server of the PR's worktree, writes each shot as an executable Claude in Chrome choreography and rehearses it off camera so the take is a clean playback that needs almost no editing, films it in the recording Chrome with aditor, and writes a "### Demo" section at the top of the PR body with the video and a short pt-BR text explaining what it shows. Never opens a browser, a server or a PR edit on its own initiative.
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
5. Choreograph each shot and rehearse it with no camera running.
6. Film, shot by shot, by replaying the choreography.
7. Trim the ends.
8. Attach and publish the `### Demo` section.
9. Ask what to tear down.

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
- **Arrive at the screen the way a user arrives.** Open on the home page, or on whatever screen the
  person is really on before the feature, and reach the target through the menu or the link the
  product offers, not by pasting its URL. A demo of something that reacts to arriving somewhere (a
  modal, a badge, a toast, an empty state turning full) is worthless if it is already on screen in
  the first frame: that reads as a screenshot and hides the very thing under test, which is *when*
  it shows up. Roll the camera on the previous screen, navigate, let it appear, then act on it.
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

The film comes from the recording Chrome, not the everyday one. `aditor record --tab` pulls frames
from a tab over the DevTools protocol, so it needs a Chrome with a debug port, and the everyday one
can never have it: Chrome 136+ refuses `--remote-debugging-port` on the default data dir, and a
second launch on a data dir that is already running only forwards to the live instance and exits.
So there is a second Chrome, the **Chrome Gravação** shortcut on the desktop:

| | |
|---|---|
| Data dir | `~/.config/google-chrome-record` |
| Profile | `Default`, a copy of the everyday `Claude` profile (`Profile 3`) |
| CDP port | `9222`, shared by every profile open in that instance |
| Window class | `chrome-gravacao` |

```bash
command -v aditor >/dev/null || echo "aditor missing"
curl -sf --max-time 2 http://127.0.0.1:9222/json/version >/dev/null && echo up || echo down
```

`down`: bring it up with the command the shortcut runs. The everyday Chrome keeps running next to
it; never kill it to free the port.

```bash
nohup /usr/bin/google-chrome \
  --user-data-dir="$HOME/.config/google-chrome-record" \
  --remote-debugging-port=9222 --class=chrome-gravacao \
  --no-first-run --no-default-browser-check >/dev/null 2>&1 &
until curl -sf --max-time 1 http://127.0.0.1:9222/json/version >/dev/null; do sleep 0.5; done
```

The profile copy carries the logins and the Claude in Chrome extension, but it is **frozen at the
moment it was made**. A sign-in it no longer has: ask the user to sign in in that window, never type
a password. To refresh the whole copy, with the recording Chrome closed:

```bash
rsync -a --delete \
  --exclude 'Cache/' --exclude 'Code Cache/' --exclude 'GPUCache/' --exclude 'Service Worker/' \
  --exclude 'Shared Dictionary/' --exclude 'Singleton*' \
  "$HOME/.config/google-chrome/Profile 3/" "$HOME/.config/google-chrome-record/Default/"
```

Open the target with `/usr/bin/google-chrome --user-data-dir="$HOME/.config/google-chrome-record"
"<url>"`, which lands in the running window. The tab id for `record` comes from
`aditor tabs --cdp-port 9222 --json`, matched **by URL**, never by position: the first entry is
often `chrome://newtab/`, and the order changes as tabs get focus. While the port is up any local
process can drive that browser and read its cookies, which is why teardown offers to close it.

The frames are the page viewport only: no address bar, no tabs, no cursor, no audio. Three
properties of the capture change the direction:

- **The cursor is not in the frames.** Every click is invisible, so the film needs the page's own
  feedback (focus ring, spinner, flash message, row appearing) to carry each beat. A shot whose
  only evidence is "the cursor moved there" cannot be filmed; add a caption in step 7 instead.
- **The frame size is fixed at the first frame.** Size the window before rolling and leave it
  alone. No DevTools, no resize, no zoom during a take.
- **The file's resolution is the tab's viewport, in device pixels.** The recording window on this
  machine is already calibrated so a take comes out at 1920x1080; there is nothing to force, and
  `aditor` has no scale flag anyway, at capture or at convert. Just do not touch the window:
  resizing it, opening DevTools or zooming the page changes the viewport and the film silently
  comes out at some other size. A take whose `aditor info` reports anything other than 1920x1080
  means the window was disturbed, so fix the window and film again rather than scaling in post,
  which only blurs it.

To drive the page with Claude in Chrome rather than by hand, the recording instance has to be the
selected browser: `list_connected_browsers`, then the mandatory `AskUserQuestion` listing every
connected browser, then `select_browser`. Never pick one silently. The instance not on the list
means driving it by hand, which is fine and worth one line in the report.

### 5. Choreograph the shot, then rehearse it

**The camera records wall clock time, including your thinking.** A shot driven by deciding what to
click next, calling `read_page` to find it, taking a screenshot to check, then clicking, is three
minutes of footage for eight seconds of product. Cutting that back down afterwards costs a pile of
edits, a generation of quality per edit, and a film that still moves in lurches, because the pauses
are between the actions and no trim removes them.

So the route is written as an **executable script before the camera exists**, rehearsed until it
runs clean, and the take is nothing but the playback.

**Write the choreography.** One numbered line per action, in the exact form it will be called, with
every value already resolved: tab id, url, coordinate or ref, wait duration. No branches, no "find
the button", no "check whether it worked". A line that cannot be written with its values filled in
is not ready to film.

```
1. navigate      tab=68049904  url=http://localhost:3002/
2. wait          2s                        (home settles, this is the thumbnail)
3. left_click    coordinate=[820, 61]      (menu Relatórios)
4. wait          3s                        (index loads, modal fades in)
5. left_click    coordinate=[825, 596]     (Experimentar agora)
6. wait          4s                        (report builder renders)
```

**Rehearse it end to end with no camera running.** The rehearsal is where the ref that does not
navigate, the coordinate that lands two pixels off the button, the modal that needs one more second
and the screen that is not where you assumed all show up, and where they cost nothing. Note the
values that actually worked, and the wall clock the whole run took: that number is the length of
the film, and if it is over the shot's budget the fix is fewer steps, here, not a trim later.

**Put the state back to the starting point** after the rehearsal: the preference the run consumed,
the record it created, the screen it ended on. A rehearsal that leaves the feature already dismissed
films nothing.

**Then roll, and run the script without thinking.** Batch the actions with `browser_batch` so a
sequence goes out in one call instead of one round trip per click. Inside the take:

- **No `read_page`, no `find`, no screenshot.** Each one is seconds of a frozen screen in the middle
  of the film, and none of them appear in the frames. They belong to the rehearsal.
- **Waits are deliberate and short.** Long enough for the page to settle and for a human eye to
  register what changed, never "wait and see".
- **A step that misfires ends the take.** Stop, fix the choreography line, put the state back, film
  again. Do not improvise on camera: improvisation is exactly the footage that has to be cut out.

The output of this step is a take that is already roughly the right length and moves at one pace,
which is what makes step 7 a trim of the ends instead of a rescue operation.

### 6. Film

**One take per shot**, into the evidence folder, never one long take for the whole route. A
fumbled step then costs one retake instead of the film.

The take is the **playback of the rehearsed choreography** and nothing else: start the recorder,
send the batched actions, stop the recorder. Anything you would have to decide between two lines
was supposed to be decided in step 5.

```bash
EVIDENCE="$ROOT/tmp/demo/pr-<number>"; mkdir -p "$EVIDENCE"
REC=$(aditor record --tab "$TAB" --cdp-port 9222 --crf 18 --preset slow \
      -o "$EVIDENCE/<n>-<slug>.mp4" --yes --json \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
# replay the choreography, batched, no reads in between
aditor stop "$REC" --json
```

**`--crf 18 --preset slow`, not the defaults.** What is on screen is a web app: thin text, one
pixel borders, flat fills. The defaults (`--crf 20 --preset veryfast`) are tuned for camera
footage and turn small type into mush the moment anything scrolls or a modal fades in, which is
exactly the moment the shot exists for. The file grows a little; nobody ever complained that a
15 second demo was 900 KB instead of 350 KB.

Between shots: land on the next starting screen **before** the next `record` call, so no take opens
on a loading page.

After each take, read `duration` and `size_bytes` from `stop`. A duration far under the wall clock,
or a handful of kilobytes for a busy screen, is a dropped take. Redo it before moving on, because
a missing shot is only discovered at stitch time otherwise.

A shot that fails for a reason in the product is a **finding**, not a retake. Stop filming, report
it, and let the user decide whether the PR still deserves a demo.

### 7. Trim the ends

A rehearsed take is already close to the right length, so this step is **one trim per shot, of the
dead air at the head and the tail**, plus one caption. Editing is not where a demo is made; it is
where a rehearsed demo is tidied. Reaching for a chain of cuts to rescue a three minute take means
step 5 was skipped, and the fix is to film it again from the choreography, not to keep cutting.

Post-production is the same tool:

Every editing subcommand takes the input as a **positional** argument, writes to `-o`, and needs
`--yes` to overwrite. Trim each take first, then caption it, then stitch:

```bash
aditor cut --from 0:02 --to 0:11 --codec copy -o 1-cut.mp4 --yes 1-raw.mp4
aditor write --text "Filtro salvo pelo usuário" --from 0 --to 3 \
             --x 40 --y 40 --font-size 42 --color 'white@0.9' \
             --crf 18 --preset slow -o 1-final.mp4 --yes 1-cut.mp4
```

**Count the generations.** Every editing subcommand except `cut --codec copy` decodes and
re-encodes the whole file, and the loss stacks: cut, then caption, then speed, then append is four
generations over the raw take, and by the fourth the UI text has visibly crumbled. Budget **two**
per shot, cut and caption, and carry `--crf 18 --preset slow` on every one that re-encodes. Drop
`speed` unless the shot really drags; slowness is a shot list problem, and fixing it in post costs
a generation.

`cut --codec copy` does not re-encode at all, so it is free, but it can only cut at a keyframe and
will land a fraction of a second off the mark. That is the right trade for trimming dead air at the
ends. When a cut has to be frame exact, drop `--codec copy` and pay the generation with
`--crf 18 --preset slow`.

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
| Under 10 MB | GitHub caps attachment size by plan, and nobody should wait on a download to review. A rehearsed 60 second take at `--crf 18` lands well under it |

Over 10 MB: re-encode instead of cutting content, and climb the CRF one step at a time,
`aditor convert --crf 23 --preset slow -o small.mp4 --yes demo.mp4`, then `aditor info` again. Only
if it is still over does `--crf 26` come next. Jumping straight to a high CRF throws away the very
thing the demo is made of, which is readable UI text. Still over at 26: the route was too long, and
the fix is fewer shots, not a blurrier film.

A demo of a screen full of text that comes out at a few hundred kb/s is not a small file, it is a
soft one. Read the bitrate from `aditor info` and, when the frames look mushy, the fix is at the
`record` call (`--crf 18 --preset slow`) and in the number of generations, never a sharpening pass
afterwards.

### 8. Attach and publish

The file reaches the PR through `gh pr edit --attach`, which uploads it and writes the asset URL
into the body. No browser, no drag and drop, nothing to paste back by hand.

The URL has to end up inside a `### Demo` section at the **top** of the body, and `--attach` with no
body flag appends it to the **end**, so this is two commands: upload first, then rebuild the body
around the URL it produced.

```bash
gh pr edit <number> --attach "$EVIDENCE/demo.mp4"
gh api "repos/{owner}/{repo}/pulls/<number>" --jq .body > /tmp/pr-body.md
# cut the appended asset URL off the end, put it inside the ### Demo block at the top, then
gh api -X PATCH "repos/{owner}/{repo}/pulls/<number>" -F body=@/tmp/pr-body.md
gh api "repos/{owner}/{repo}/pulls/<number>" --jq .body | head -40
```

Four properties of `--attach` decide how this step goes:

- **A video takes no alt text.** The `<file>#<alt text>` form exists for images. A video renders as
  a player and cannot carry alt text, so a `#` on the path is an error, not a caption. The caption
  is burned into the frames in step 7, and the explanation goes in the pt-BR text under the player.
- **A reference in the body is rewritten in place.** When the body being sent already points at the
  local file, `--attach` swaps that reference for the uploaded URL instead of appending, which
  collapses the two commands into one. That behaviour is documented with image syntax
  (`![alt](./login.png)`); before relying on it for a video, send it and read the body back. If the
  reference survived verbatim, fall back to the two-command order above.
- **A non-zero exit does not mean nothing landed.** When several attachments are sent and only some
  upload, the PR is still edited with the ones that made it, the command exits non-zero, and the
  PR URL is still printed. Read the body before concluding anything and before refilming.
- **Up to 50 files per call**, which only matters when a run publishes stills alongside the film.

The body itself goes through `gh api -X PATCH` rather than `gh pr edit --body`, for one reason:
the read-back afterwards is the only proof that the section landed, at the top, with the rest of
the body intact. A silent no-op looks exactly like a success.

Where the section goes, and what it looks like:

- **At the very top of the body, above everything.** The film is what a reviewer opens the PR to
  see, and a section at the end is a section nobody scrolls to. The description, the test plan and
  the ISO 42001 block all stay where they are, below it.
- **Replace, never append.** A `### Demo` section already in the body is this skill's own previous
  run: swap its contents in place, so a second demo does not stack two videos.
- **Everything else in the body is untouched.** The template sections, the test plan, the
  screenshots and the `<!-- iso42001:start -->` block belong to the author and keep their order.

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

### 9. Teardown

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
| "I will figure out the route while recording and cut it later" | The camera records your thinking as dead footage, and no trim removes a pause that sits between two actions. Choreograph, rehearse, then roll. |
| "A rehearsal is a waste, it doubles the work" | The rehearsal is where the ref that does not click and the wait that is too short cost nothing. On camera they cost the take. |
| "I will screenshot mid-take to check it worked" | It freezes the film for seconds and never shows up in the frames. Checks belong to the rehearsal. |
| "One action per call is fine" | Each round trip is wall clock time in the film. Batch the choreography with `browser_batch`. |
| "The take is not 1080p, I will upscale it" | Resolution comes from the tab's viewport and the window is already calibrated for it. Something moved the window; fix that and refilm. |
| "I will open the feature's URL directly, it saves five seconds" | The viewer never sees where the feature lives or when it reacts. Start on the home screen and navigate there like a user. |
| "The modal is already open, that is the shot" | A thing that is on screen in frame one is a screenshot. Film it appearing. |
| "The default encoder settings are fine" | They are tuned for camera footage. UI text needs `--crf 18 --preset slow`, at capture and at every re-encode. |
| "One more editing pass will not hurt" | Each pass is a generation of loss. Two per shot, cut and caption. |
| "It is 3 minutes but it is all relevant" | Under 60 seconds. Relevance is what the shot list is for. |
| "I will paste the video URL as a markdown link" | Only a bare URL on its own line renders a player. |
| "`gh pr edit --body` does the body too, one command for everything" | The upload is `gh pr edit --attach`, but the body goes through `gh api -X PATCH` and gets read back. That read-back is the only proof the section landed at the top with the rest intact. |
| "I will append the Demo section, the old one is further up" | Replace it. Two players in one body is this skill running twice. |
| "The body has a weird HTML comment block at the end, I will drop it" | That is the ISO 42001 record. It stays where it is; the Demo section goes to the top of the body, not next to it. |
| "The description should come first, the video goes after it" | The video is the first thing the reviewer should see. `### Demo` is the first section of the body. |
| "I will open the browser and drag the file into the PR" | `gh pr edit --attach` uploads it from the command line. The browser is for filming, not for publishing. |
| "The command exited non-zero, so nothing was attached" | A partial upload still edits the PR and still prints its URL. Read the body before refilming. |
| "The video needs alt text like a screenshot does" | A player carries none. `#alt` on a video path is an error. The caption is in the frames and in the text under it. |
| "The everyday Chrome is already signed in, I will film there" | It has no debug port and never will. Only the recording instance has tab ids on 9222. |
| "browser-test left a server on another worktree's port, close enough" | Another worktree is another commit. Detect by cwd. |

## When NOT to use

- Proving the PR works, with findings and evidence: `/soffner:browser-test`.
- Still screenshots for the PR body: take them in `/soffner:browser-test` and attach them the same way step 8 describes.
- The PR is not open yet: open it first, since the section is written into its body.
