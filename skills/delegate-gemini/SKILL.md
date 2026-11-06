---
name: delegate-gemini
description: Use when a well-bounded slice of the current work can go to Gemini 4 Argon through the Antigravity CLI (manda pro Gemini, pede uma segunda opinião ao Gemini, delegate to Gemini), or `/delegate-gemini <task>` is invoked. Good for a second opinion on a diff, a search or inventory across the code, or a summary of a big log or dataset. Runs one closed task with `agy` in the background, checks everything that comes back before using it, and reports the tokens spent. Never for the final call.
---

# delegate-gemini

```
/delegate-gemini <task>
```

Opus hands Gemini 4 Argon one closed piece of the work and checks what comes back. Gemini's answer is input, never a decision.

| Good use | Bad use |
|---|---|
| Second opinion on a diff review | The final call on anything |
| Search or inventory across the code | Manual testing |
| Summary of a big log or big data | Work that depends on the board's or the slot's conventions |

Gemini opens no subagents: one task per call, closed, with an output you can verify.

Cost and time: 2 to 3× slower than Opus. Until 2026-11-30 a token costs half of Opus; from 2026-12-01, the same. Billing goes to the GCP project `v360-gemini-enterprise`, not to the Claude limit.

## 1. Pick the mode

There is no interaction: a denied command ends the run with no response. `--mode auto` does not exist on this machine, even though `--help` lists it.

- **Read only** → `--mode plan`, run from the work folder.
- **Runs commands or edits** → `--dangerously-skip-permissions`, and only in a disposable worktree of its own, never the one Opus is working in. `git worktree add --detach <tmp>/wt HEAD`, run from there, and `git worktree remove --force <tmp>/wt` once you took what you need.

Never allow a push or any GitHub write: say it in the prompt, and run `agy` with the guard env from step 3, which breaks `git push` to origin and `gh` auth for that process only.

## 2. Write the prompt

`agy` reads `AGENTS.md` and `GEMINI.md` only, never `CLAUDE.md` or `.claude/rules`. The prompt carries the context and the rules that matter, or lists the files it must read. Save it to `<tmp>/prompt.md` (`<tmp>` is a fresh `mktemp -d`, reused literally in later calls) with:

- the task in one sentence and its scope (files, folders, base);
- the rules that apply, pasted or as paths to read;
- the exact output shape (e.g. one line per finding with `file:line`);
- `Do not push, do not run gh, do not write to GitHub.`

## 3. Run in the background

```bash
cd <work folder> && GH_TOKEN=blocked GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.pushurl GIT_CONFIG_VALUE_0=/dev/null/no-push \
  ~/.local/bin/agy -p "$(cat <tmp>/prompt.md)" --model gemini-4-argon-high --output-format json \
  --mode plan [--add-dir <folder>] > <tmp>/out.json
```

The cwd becomes the workspace; `--add-dir <folder>` grants another (repeatable). Swap `--mode plan` for `--dangerously-skip-permissions` per step 1. It takes minutes: Bash with `run_in_background: true`, then wait for the notice instead of polling.

## 4. Check, then use

`jq -r .response <tmp>/out.json` for the answer, `jq '{status, usage}' <tmp>/out.json` for the rest.

- A failed `status` or an empty `response` usually means a denied command. Narrow the task or fix the mode; never rerun the same call hoping for another result.
- Check every claim against the code before using it: open the `file:line`, rerun the search. Drop what does not hold.
- In reviews Gemini inflates severity (High for what is Medium or Low). The final classification is Opus's.
- A writable run: read `git status` and `git diff` in its worktree yourself. Nothing reaches the real worktree without that.

## 5. Report

What went to Gemini, what held up, what was dropped, and the tokens from `usage`: `input_tokens` (uncached), `cache_read_tokens` and `output_tokens` (reasoning included).

## Example: second review of a diff

```bash
git diff <base>...HEAD > <tmp>/diff.patch
```

`<tmp>/prompt.md`:

```
Review the diff in <tmp>/diff.patch for correctness bugs only, no style.
Repo rules that apply: <pasted rules, or paths to read>.
One line per finding: file:line | High/Medium/Low | what breaks, with a concrete input.
Do not push, do not run gh, do not write to GitHub.
```

Run step 3 from the repo root with `--mode plan --add-dir <tmp>`. Cross with Opus's own findings: found by both, confirm in the code; only by Gemini, verify before adopting; only by Opus, keep. Reclassify every severity yourself.
