---
name: browser-record
description: Use when the user asks for a video of something happening in a browser (record this, film the flow, mp4 of the demo), or when another skill needs its browser steps filmed. Records one real Chrome tab with aditor over the DevTools protocol, from a duplicate of the Claude profile that keeps the logins. Never opens a browser or starts a recording because a change "would look good on video".
---

# browser-record

Film a flow in a real, signed-in Chrome tab and hand back an mp4. The capture goes through
`aditor record --tab`, which pulls frames from the tab over the DevTools protocol, so it does
not need screen recording permission and does not care whether the window is in front.

**The invocation authorizes the recording browser.** Nothing else. This skill does not start a
web server, does not touch a database and does not sign anyone in.

## What lands in the file

| Included | Excluded |
|----------|----------|
| The page viewport, at its current size, 30 fps, h264 | Address bar, tabs, window frame |
| Everything the page paints, including animations and Turbo swaps | The mouse cursor and click ripples |
| | Audio of any kind |

Two consequences worth planning around before pressing record:

- **A click is invisible.** The cursor is not composited into the frames, so a viewer sees the
  result of a click and never the click. Narrate the steps in the report, or drive slowly and
  let the page's own hover and focus states carry the story.
- **The frame size is fixed when recording starts.** Resizing the window or opening DevTools
  mid-take changes the viewport and ends the capture with an error. Set the window up first.

## The browser this records

A second Chrome, separate from the everyday one, launched by the **Chrome Gravação** shortcut on
the desktop:

| | |
|---|---|
| Data dir | `~/.config/google-chrome-record` |
| Profile | `Default`, a copy of the everyday `Claude` profile (`Profile 3`) |
| CDP port | `9222` |
| Window class | `chrome-gravacao`, so the dock separates it from the everyday Chrome |

Why it cannot be the everyday Chrome, both reasons verified on this machine:

1. Chrome 136 and up refuse the debug port on the default data dir. The message lives in the
   binary itself: `DevTools remote debugging requires a non-default data directory. Specify this
   using --user-data-dir.`
2. A second `google-chrome` on a data dir that already has an instance does not become a new
   process. It talks to the running one through its singleton socket and exits, so the flag never
   takes effect on a browser that is already up.

Having several profiles was never the blocker. One instance exposes the tabs of **every** profile
open inside it on the same port, so the port belongs to the instance, not to the profile.

The copy carries cookies, `Login Data`, local storage, history and extensions, the Claude in Chrome
extension among them, which is what lets Claude in Chrome drive this instance the same way it
drives the everyday one. **The copy is frozen at the moment it was made**, so a login done later in
the everyday Chrome is not there. Refresh it with the browser closed:

```bash
rsync -a --delete \
  --exclude 'Cache/' --exclude 'Code Cache/' --exclude 'GPUCache/' --exclude 'Service Worker/' \
  --exclude 'Shared Dictionary/' --exclude 'Singleton*' \
  "$HOME/.config/google-chrome/Profile 3/" "$HOME/.config/google-chrome-record/Default/"
```

While the port is up, any local process can drive that browser and read its cookies. Close the
window when the recording is done.

## Arguments

`/browser-record [what to record]`

| Token | Rule |
|-------|------|
| what to record (optional) | Free text: the flow, the URL, the PR. Missing: ask what to film in one question and stop until answered. Filming the wrong thing costs a full retake. |

## Flow

### 1. Preflight

```bash
command -v aditor >/dev/null || echo "aditor missing"
curl -sf --max-time 2 http://127.0.0.1:9222/json/version >/dev/null && echo up || echo down
```

`down` means bring it up with the same command the desktop shortcut runs:

```bash
nohup /usr/bin/google-chrome \
  --user-data-dir="$HOME/.config/google-chrome-record" \
  --remote-debugging-port=9222 --class=chrome-gravacao \
  --no-first-run --no-default-browser-check >/dev/null 2>&1 &
until curl -sf --max-time 1 http://127.0.0.1:9222/json/version >/dev/null; do sleep 0.5; done
```

The everyday Chrome keeps running untouched next to it. Never kill it to free the port, and never
try to put the port on it.

### 2. Get the page ready

Open the target in that instance. A plain launch on the same data dir forwards to the running
window instead of starting a second one:

```bash
/usr/bin/google-chrome --user-data-dir="$HOME/.config/google-chrome-record" "<url>"
```

If the page needs a sign-in the copy no longer has, stop and ask the user to sign in **in that
window**. Never type a password and never read a credentials file.

To drive the page with Claude in Chrome instead of by hand, list the connected browsers and select
the recording one before any navigation, so the steps and the frames come from the same window.
If the recording instance is not on that list, drive it by hand or hand the steps to the user, and
say so in the report rather than filming the wrong window.

Settle the window size now. It is the frame size for the whole take.

### 3. Roll

```bash
aditor record --tab "<TAB_ID>" --cdp-port 9222 -o "<OUT>.mp4" --yes --json
```

Tab ids come from `aditor tabs --cdp-port 9222 --json`. Match the tab by URL, never by position:
the first entry is often `chrome://newtab/`, and Chrome reorders the list as tabs get focus.

Without `--duration` the call returns immediately and the capture runs in the background. Keep
the `id` field of that JSON, which is what stops it. It is `id`, not `recording_id`:

```json
{ "id": "rec-1789065645-258010", "pid": 258012, "output": "...", "log": "..." }
```

With `--duration 10` it blocks for ten seconds and exits instead, which suits a fixed-length take
that needs no interaction.

`--selector '#some-id'` crops to one element, recomputed every frame. Use it for a widget demo,
and only on a container that does not move or resize, since either ends the capture with an error.

### 4. Stop and check

```bash
aditor stop "<REC_ID>" --json
aditor info "<OUT>.mp4"
```

`stop` returns the real `duration` and `size_bytes`. Read them: a take that reports a duration far
under the wall clock, or a size of a few kilobytes for a busy page, means frames were dropped and
the take has to be redone. A recording that failed mid-way leaves its reason in the log file the
`record` call named.

Editing, if the take needs it, is the same tool: `aditor cut --from --to`, `aditor speed -x 1.5`,
`aditor crop`, `aditor write` for a caption on a frame, `aditor append` to stitch takes.

### 5. Report

```
## browser-record: <what was filmed>

File: <path>  (<duration>s, <WxH>, <size>)
Tab: <url>
Steps filmed: <one line per step, in order, since the cursor is not in the frames>
Notes: <retakes, anything the take does not show>
```

Then say the recording browser is still open and that closing its window is the way to release the
debug port. Do not close it unasked. Most of the time the next request is another take.

## Where the file goes

| Situation | Path |
|-----------|------|
| Called on its own | `~/Documents/Videos/<slug>-<YYYYmmdd-HHMM>.mp4`, which is also aditor's own default directory |
| Called by another skill | inside that skill's evidence folder, under the name it asks for |

## Called from another skill

The contract is three calls, and the caller owns the middle one. `browser-test` is the case this
was built for: it already drives Chrome row by row and already has an evidence folder.

```bash
REC=$(aditor record --tab "$TAB" --cdp-port 9222 -o "$EVIDENCE/<nn>-<row-slug>.mp4" --yes --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
# the caller runs its own steps here
aditor stop "$REC" --json
```

Three things a caller has to respect:

- **One take per row, not one per run.** A single file covering every row is unwatchable and one
  failed row spoils all of it.
- **The tab has to live in the recording instance.** A tab in the everyday Chrome has no id on
  port 9222, and `aditor record` will not find it.
- **Recording does not authorize anything else.** The caller's own gates on servers, databases and
  settings are unchanged by filming them.

## Rationalizations that mean stop

| Thought | Reality |
|---------|---------|
| "I will just put the debug port on the Chrome that is already open" | Chrome 136+ refuses the port on the default data dir, and a second launch on a live data dir only forwards to it. The recording instance exists for exactly this. |
| "Several profiles are the problem, I need one port per profile" | One instance, one port, every profile open in it. The port belongs to the instance. |
| "The everyday Chrome has the session, I will kill it and reuse its profile dir" | Never kill the user's browser. The copy already carries the session, and a stale copy gets refreshed with the rsync above. |
| "The window looks small, I will resize while it records" | The frame size is fixed at the start. Resizing ends the take with an error. Size first, roll second. |
| "The viewer will follow the clicks" | The cursor is not in the frames. Narrate the steps in the report or the video is a mystery. |
| "The file exists, so the take worked" | Read `duration` and `size_bytes` from `stop`. A near-empty file is a failed take that looks like a success. |
| "I will record the first tab in the list" | The first tab is usually the new tab page, and the order changes with focus. Match by URL. |
| "This change would look great on video, let me film it" | This skill runs when it is invoked, never on its own initiative. |
| "I will close the browser to clean up" | Teardown is the user's call. They usually want a second take. |

## When NOT to use

- Screenshots are enough: `computer` `screenshot` through Claude in Chrome, no recording browser needed.
- The whole screen, or a window with its browser chrome, is what matters: `aditor record --video-device :0.0`, which needs no debug port at all.
- Validating that a PR works, rather than filming it: `/soffner:browser-test`.
- A demo of a PR, planned as a route and published on the PR body: `/soffner:demo`, which uses this skill for the takes.
- A stop-motion of stills stitched with ffmpeg, on a throwaway profile with no session: that is a different tool, and it does not need this browser.
