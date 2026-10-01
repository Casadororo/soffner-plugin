---
name: demo
description: Use when the user asks for a demo video of a pull request (record a demo, film the PR, put a video on the PR). Plans a shot list from what the PR delivers, reuses or starts the dev server of the PR's worktree, signs in as the PR's temporary user, writes each shot as a Playwright script and rehearses it with the camera off, films every shot in one headless run with an animated cursor, chapter cards and pt-BR captions drawn live on the page, saves the film to ~/Videos and writes a "### Demo" section at the top of the PR body with the video and a short pt-BR text explaining what it shows. Never opens a server or a PR edit on its own initiative.
---

# demo

Turn a pull request into a short film a reviewer can watch instead of checking it out. Same
discipline as `/soffner:browser-test`, different deliverable: that one proves the PR works and
reports findings, this one shows the PR working and publishes the result on the PR.

**The invocation authorizes the dev server of this worktree, a headless browser of this run's own,
this PR's temporary user (created or refreshed as [Sign-in](#4-recorder-and-sign-in) describes) and
one edit to the PR body.** It does not authorize a comment, a review, a commit, a push, or any other
write to the database beyond what a user of the feature does through the screen.

A demo is a **happy path**. If the route hits a bug, the take stops and the bug is reported. Do
not film around it, and do not fix it: fixing is a separate request, and Rails reloads under the
remaining shots anyway.

## Arguments

`/demo [pr] [what to show]`

| Token | Rule |
|-------|------|
| `pr` (optional) | `123`, `#123`, a URL or a branch. Missing: the PR of the current branch. No PR there either: ask and stop. |
| `what to show` (optional) | Free text narrowing the route to one behavior. Missing: the route covers what the PR body and the diff deliver. |

## Where things go

| What | Where |
|------|-------|
| The film | `$HOME/Videos/demo-pr-<number>-<sha>.mp4`, the only file meant to outlive the run |
| Everything else (shot scripts, rehearsal screenshots and accessibility trees, the signed-in session, encoder scratch) | `$WORK="$ROOT/tmp/demo/pr-<number>"`, gitignored |

`<SKILL_DIR>` is the base directory shown when this skill was loaded. The recorder is
`<SKILL_DIR>/demo-take.js`.

## Flow

1. PR, worktree and the state already on the machine.
2. Shot list.
3. Server.
4. Recorder and sign-in.
5. Write each shot and rehearse it with the camera off.
6. Film every shot in one run.
7. Check the film.
8. Attach and publish the `### Demo` section.
9. Ask what to tear down.

### 1. PR, worktree and what is already running

```bash
gh pr view <pr> --json number,title,url,state,headRefName,baseRefName,isDraft
git branch --show-current && git rev-parse --short HEAD
```

Current branch is not `headRefName`: invoke `/soffner:dono <number>` with no task to land in the
PR's worktree, then continue from step 2 inside it. Never film a PR from another branch's
checkout. The SHA goes in the file name and in the demo text, because the film shows that commit
and no other.

**Assume a server is already up.** This is normally run right after `/soffner:browser-test` or
`/soffner:browser-test-auto`, which leave the server running and the PR's temporary user in place
on purpose. Check before starting anything, and reuse what answers:

```bash
ROOT="$(git rev-parse --show-toplevel)"
for pid in $(pgrep -f '^puma [0-9.]+ \(tcp://'); do
  [ "$(readlink /proc/$pid/cwd)" = "$ROOT" ] && tr '\0' ' ' < /proc/$pid/cmdline && echo
done
WORK="$ROOT/tmp/demo/pr-<number>"; mkdir -p "$WORK" "$HOME/Videos"
```

Anything reused gets said in the report, so the reader knows the film came from a server this run
did not start.

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
| # | Shot | Route | Actions | What it proves | Chapter / captions (pt-BR) | Seconds |
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
  PR's own flag, a write outside the browser, a change to a pre-existing record, a permission the
  temporary user does not have yet) is the same gate `/soffner:browser-test` applies. Ask before,
  one question, and mark the shot dropped if the answer is no.

Print the shot list before filming. It is information, not a gate, but it is also the last cheap
moment to change the route.

### 3. Server

Reuse the one found in step 1. None found: start the project's dev server in the background from
`$ROOT` (V360: `bin/devq`; inside a devslot slot, through the slot's `bin/devslot` as
`/soffner:browser-test-auto` describes), read the port it announces, wait for `Listening on`.

```bash
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:<port>/"
```

`200` or `302` and the server is fine. The base URL is `http://localhost:<port>` (inside a devslot
slot, `http://devslotN.localhost:<port>`), **never `127.0.0.1`**: an app that resolves the account
from the hostname does not recognise the literal IP and answers its own 404 on every route, which
on film looks like a broken feature. A `500` with pending migrations is a gate, not a chore.

### 4. Recorder and sign-in

**The recorder.** `demo-take.js` drives the machine's Chrome headless through Playwright and films
it with Chrome's own screencast. Nothing opens on the operator's screen, nothing touches the
operator's Chrome, and every run gets a fresh, isolated browser. The first run on a machine installs
the pinned Playwright into a cache of its own (no browser download: it uses the installed Chrome;
`ffmpeg` comes from `PATH`):

```bash
PW_DIR="$HOME/.cache/soffner-demo"
[ -d "$PW_DIR/node_modules/playwright" ] || \
  npm install --prefix "$PW_DIR" --no-audit --no-fund playwright@1.64.0-alpha-2026-10-01
```

The pin is a 1.64 prerelease because `showActions({ style })`, which hides the action title that
would otherwise print Playwright code on screen, first ships in 1.64. Move it to `1.64.0` once that
is released.

What the capture gives, and what that changes in the direction:

- **The cursor is in the frames.** A drawn pointer travels to every click and hover, so the viewer
  sees where each action lands. The page's own feedback (spinner, flash message, row appearing)
  still carries the beat; the cursor only says where to look.
- **Text is drawn live, not burned in afterwards.** `cam.chapter` shows a centred card over a
  blurred page, `cam.caption` a line at the bottom. No editing pass, so no generation loss.
- **The frame is the viewport.** `VIEWPORT` (default `1920x1080`) is both the browser size and the
  file's resolution. Chrome never films above the CSS viewport, so there is no scaling to tune.
- **Frames come only when the page paints, with their real time.** Every still longer than
  `HOLD_MAX` (default 2.5 s) is cut down to it at encode time, so a wait that ran long costs one
  short pause on film instead of a frozen screen.

**Sign-in.** The browser is isolated, so it starts signed out. It signs in as this PR's temporary
user, never as the operator: follow the section "Temporary user (V360)" of
`<SKILL_DIR>/../browser-test-auto/SKILL.md` (same user, `teste_browser_pr<number>`, reused when
`/soffner:browser-test-auto` already made it; same least-privilege role; same first-access step,
whose proof lines have to read zero). The one change is where the password lives: it is generated in
the shell and reaches both the Ruby that sets it and the sign-in script through the environment, **in
the same Bash call**, so it is never printed, never in a file and never in the conversation.

Write `$WORK/0-sign-in.js`. For V360:

```js
module.exports = {
  async take(page) {
    await page.goto('/users/sign_in');
    const portal = page.locator('#login_portal'); // shown when the tenant also offers SSO
    if (await portal.isVisible()) await portal.click();
    await page.locator('#pre_otp_login').fill(process.env.DEMO_EMAIL);
    await page.locator('#step-1 input[name="user[password]"]').fill(process.env.DEMO_PASSWORD);
    await page.locator('#step-1 [type=submit]').click();
    await page.waitForURL(url => !url.pathname.startsWith('/users/sign_in'));
  },
};
```

```bash
export DEMO_EMAIL='<temporary user email>'
export DEMO_PASSWORD="$(ruby -rsecurerandom -e 'print SecureRandom.alphanumeric(16), "aZ9!"')"
bin/rails runner "$WORK/temp-user.rb"   # creates or refreshes the user, password from ENV['DEMO_PASSWORD'], prints the proofs
BASE_URL=http://localhost:<port> SAVE_STORAGE="$WORK/auth.json" \
  node <SKILL_DIR>/demo-take.js rehearse "$WORK/0-sign-in.js"
```

Then open `$WORK/0-sign-in.png`: the header has to show the temporary user. Delete
`$WORK/0-sign-in.aria.txt` once read, since a failed sign-in leaves the filled form in it.
`$WORK/auth.json` is the signed-in session every later command loads with `STORAGE`.

### 5. Write each shot, then rehearse it

**The camera records wall clock time.** The recorder takes that off the table by running a script,
not a conversation: nothing is decided while it films. So every shot is written as a Playwright
script before the camera exists, rehearsed until it runs clean, and the take is nothing but the
playback.

One file per shot, `$WORK/<n>-<slug>.js`, run in the order of their names:

```js
module.exports = {
  // camera off: the state the shot needs, and the screen the first frame shows
  async setup(page) {
    await page.goto('/');
    await page.getByRole('link', { name: 'Relatórios' }).waitFor();
  },
  // camera on: only what the viewer should watch
  async take(page, cam) {
    await cam.chapter('Relatórios personalizados', 'Do menu ao relatório pronto');
    await cam.caption('Abrindo o construtor');
    await page.getByRole('link', { name: 'Relatórios' }).click();
    await page.getByRole('button', { name: 'Experimentar agora' }).click();
    await page.getByRole('heading', { name: 'Novo relatório' }).waitFor();
    await page.waitForTimeout(1500);
  },
};
```

Rules for the script:

- **Locators from what the user reads**, found in the diff's views and locale files: `getByRole`
  with its accessible name, `getByLabel`, `getByText`. Never a coordinate, and never a generated id
  or a class chain that will not exist next week.
- **Wait for the thing, not for the page.** V360 screens arrive by Turbo, so the page reports itself
  loaded long before the table exists. `locator.waitFor()` on the element the beat is about, or
  `page.waitForURL`. `waitForLoadState` proves nothing.
- **Then a deliberate pause** (`page.waitForTimeout`, around 1 to 1.5 s) where a human eye needs to
  register what changed. Pauses beyond `HOLD_MAX` are cut anyway, so a long one is wasted script.
- **Type what the viewer should read** with `locator.pressSequentially(text, { delay: 60 })`; `fill`
  everything else.
- **`await` each caption** before the action it describes, or it shows up after the action instead
  of with it. Captions and chapter cards are pt-BR, because they are published to a pt-BR audience:
  this is the one text the skill writes in pt-BR, keep it that way.
- A shot without `setup` continues from where the previous one ended, which is how two shots join
  without a reload.

**Rehearse with the camera off**, all shots in order, against the signed-in session:

```bash
cd "$WORK" && BASE_URL=http://localhost:<port> STORAGE="$WORK/auth.json" \
  node <SKILL_DIR>/demo-take.js rehearse <the shot files in order>
```

Every shot leaves `<shot>.png` and `<shot>.aria.txt` (the page's URL and accessibility tree)
beside it, of where it ended. A shot that fails stops the run, prints which shot and which step, and
leaves the same two files of where it stopped. That tree is where the right locator comes from: read
it, fix the line, rehearse again. Open the PNGs in one batch once it runs clean: a script that ran is
not yet a shot that shows the right thing.

`wall_seconds` in the output is roughly the length of the film. Over the shot list's budget: the fix
is fewer steps here, never a trim later.

**Put the state back to the starting point** after the rehearsal: the preference the run consumed,
the record it created, the screen it ended on. A rehearsal that leaves the feature already
dismissed films nothing. Prefer doing that in each shot's `setup`, so every run, the take included,
starts from the same state on its own.

### 6. Film

One command, every shot, straight to the film:

```bash
OUT="$HOME/Videos/demo-pr-<number>-<sha>.mp4"
cd "$WORK" && BASE_URL=http://localhost:<port> STORAGE="$WORK/auth.json" \
  node <SKILL_DIR>/demo-take.js film "$OUT" <the shot files in order>
```

The camera runs only inside each `take`; every `setup` happens off film, and the shots join in one
encode (H.264, CRF 18, the only generation the film goes through). A misfire stops the run with the
same shot, step and screenshot as a rehearsal: fix the script, rehearse that shot, film again. A
retake costs one more run of the command, so there is never a reason to keep a fumbled take.

A shot that fails for a reason in the product is a **finding**, not a retake. Stop filming, report
it, and let the user decide whether the PR still deserves a demo.

### 7. Check the film

```bash
ffprobe -v error -show_entries stream=width,height:format=duration,size -of default=nw=1 "$OUT"
ffmpeg -v error -y -i "$OUT" -vf "fps=1/2,scale=480:-1,tile=5x6" -frames:v 1 "$WORK/contact.png"
```

Open `contact.png`: every shot shows up, in order, with its chapter and captions, the cursor on the
right controls and no screen that should not be there (a sign-in page, an error, a first-access
modal). Two hard targets before the file leaves this step:

| Target | Why |
|--------|-----|
| Under 60 seconds | A reviewer watches a minute and scrubs anything longer |
| Under 10 MB | GitHub caps attachment size by plan, and nobody should wait on a download to review |

Too long: cut steps from the scripts and film again. Over 10 MB: re-encode, climbing the CRF one
step at a time, `ffmpeg -i "$OUT" -c:v libx264 -crf 23 -preset slow -tune stillimage -movflags
+faststart <smaller>.mp4`, then `26` only if still over, and move the smaller file into place. Still
over at 26: the route was too long, and the fix is fewer shots, not a blurrier film.

### 8. Attach and publish

The file reaches the PR through `gh pr edit --attach`, which uploads it and writes the asset URL
into the body. No browser, no drag and drop, nothing to paste back by hand.

The URL has to end up inside a `### Demo` section at the **top** of the body, and `--attach` with no
body flag appends it to the **end**, so this is two commands: upload first, then rebuild the body
around the URL it produced.

```bash
gh pr edit <number> --attach "$OUT"
gh api "repos/{owner}/{repo}/pulls/<number>" --jq .body > "$WORK/pr-body.md"
# cut the appended asset URL off the end, put it inside the ### Demo block at the top, then
gh api -X PATCH "repos/{owner}/{repo}/pulls/<number>" -F body=@"$WORK/pr-body.md"
gh api "repos/{owner}/{repo}/pulls/<number>" --jq .body | head -40
```

Four properties of `--attach` decide how this step goes:

- **A video takes no alt text.** The `<file>#<alt text>` form exists for images. A video renders as
  a player and cannot carry alt text, so a `#` on the path is an error, not a caption. The captions
  are in the frames, and the explanation goes in the pt-BR text under the player.
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

The section is pt-BR, because it is published to a pt-BR team:

```markdown
### Demo

https://github.com/user-attachments/assets/<uuid>

<uma a três frases em pt-BR: o que o vídeo mostra, na ordem em que aparece, e o que o revisor
deve reparar. Sem passo a passo, sem "clique aqui". Feche com o commit filmado.>

<!-- Gravado em <sha> -->
```

Three rules on that text:

- **It describes the film, not the feature.** The PR body already explains the feature. This says
  what passes on screen, so the reviewer knows what they are looking at.
- **It names what the frames cannot.** A hover state, a keyboard shortcut, a value the viewer cannot
  read at player size: anything the captions did not cover gets a clause here.
- **It ends on the commit.** The film ages the moment someone pushes, and the SHA is what tells
  a reader whether it still describes the PR.

The bare URL on its own line is what makes GitHub render a player. Wrapping it in markdown link
syntax or an `<img>` tag gives a dead link instead.

### 9. Teardown

`$WORK/auth.json` is a live session of the temporary user: delete it once the film is published,
always. Signing in again is one command.

Then one `AskUserQuestion`, offering only what this run started:

| Offer | When |
|-------|------|
| The dev server | only if this run started it. `Keep it on <port>` first |
| The shot scripts and rehearsal files in `$WORK` | `Keep them` first. They are how a later commit gets refilmed in one command |

A server this run found already up is never offered: it belongs to whoever started it. The film in
`~/Videos` and the temporary user stay. Unanswered means everything stays, and the report says so.

## Report

```
## demo: PR #<number> <title>

Environment: <worktree>, <sha>, <base url> (<started|reused>), headless Playwright, signed in as <temp user email>
Shots: <n> filmed, <n> rehearsals, <n> dropped
File: <~/Videos/...mp4> (<duration>s, <WxH>, <size>), dead air cut: <the recorder's line, or none>
Published: <asset url> in the PR body, section ### Demo
Gates asked: <action, target, answer>
Findings: <bugs that stopped a shot, or none>
Left behind: <server, $WORK, TESTE_ records, temporary user>
```

## Rationalizations that mean stop

| Thought | Reality |
|---------|---------|
| "The shot broke, I will fix the bug and refilm" | A bug that stops a shot is a finding. Fixing reloads the app under the remaining shots and the film stops matching the PR. |
| "I will drive the recording myself, step by step, it is faster than a script" | The camera records every pause between your decisions, and no trim removes a pause that sits between two actions. Script, rehearse, then film. |
| "A rehearsal is a waste, the script is obviously right" | The rehearsal is where the locator that matches two buttons and the frame that arrives late cost nothing. On film they cost the take. |
| "The rehearsal ran clean, the film is fine" | A clean run is not a good shot. Open the rehearsal PNGs, and the contact sheet after filming. |
| "This button has no good name, a coordinate will do" | The accessibility tree in `<shot>.aria.txt` has a name for it. A coordinate breaks on the next layout change and says nothing to whoever refilms. |
| "`waitForLoadState` is enough" | Turbo screens report loaded before their content exists. Wait for the element the beat is about. |
| "I will set the data up on camera" | Preconditions go in `setup`. Nobody watches a form being filled with setup. |
| "One long shot is simpler" | One idea per shot, so a failing step names the shot and the shot list stays the story. The film is still one command. |
| "I will open the feature's URL directly, it saves five seconds" | The viewer never sees where the feature lives or when it reacts. Start on the home screen and navigate there like a user. |
| "The modal is already open, that is the shot" | A thing that is on screen in frame one is a screenshot. Film it appearing. |
| "I will burn the captions in afterwards" | Every re-encode is a generation of loss. `cam.caption` and `cam.chapter` draw them live, at zero cost. |
| "The take is 3 minutes but it is all relevant" | Under 60 seconds. Relevance is what the shot list is for. |
| "I will sign in as the operator, the session is already there" | Staff permissions, and one session per user would sign the operator out. Temporary user. |
| "I will print the password to check it" | It is generated and consumed inside one Bash call. Prove the sign-in with the header in `0-sign-in.png`. |
| "The Playwright run failed, I will film in Claude in Chrome instead" | That browser is the operator's and it takes over their screen. Fix the script; report `failed` if the recorder cannot run. |
| "I will paste the video URL as a markdown link" | Only a bare URL on its own line renders a player. |
| "`gh pr edit --body` does the body too, one command for everything" | The upload is `gh pr edit --attach`, but the body goes through `gh api -X PATCH` and gets read back. That read-back is the only proof the section landed at the top with the rest intact. |
| "I will append the Demo section, the old one is further up" | Replace it. Two players in one body is this skill running twice. |
| "The body has a weird HTML comment block at the end, I will drop it" | That is the ISO 42001 record. It stays where it is; the Demo section goes to the top of the body, not next to it. |
| "The description should come first, the video goes after it" | The video is the first thing the reviewer should see. `### Demo` is the first section of the body. |
| "I will open the browser and drag the file into the PR" | `gh pr edit --attach` uploads it from the command line. |
| "The command exited non-zero, so nothing was attached" | A partial upload still edits the PR and still prints its URL. Read the body before refilming. |
| "The video needs alt text like a screenshot does" | A player carries none. `#alt` on a video path is an error. The captions are in the frames and in the text under it. |
| "browser-test left a server on another worktree's port, close enough" | Another worktree is another commit. Detect by cwd. |

## When NOT to use

- Proving the PR works, with findings and evidence: `/soffner:browser-test` or `/soffner:browser-test-auto`.
- Still screenshots for the PR body: take them in `/soffner:browser-test` and attach them the same way step 8 describes.
- The PR is not open yet: open it first, since the section is written into its body.
