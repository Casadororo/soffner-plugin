---
name: dono
description: Use ONLY when the user explicitly invokes `/dono`. Never auto-trigger from keywords. Takes ownership of a pull request for this session - resolves the PR, makes sure a worktree with the PR branch exists (creating one through the project's worktree flow when it does not), syncs with the remote, loads the PR context and, when the prompt carries a task, executes it inside that worktree. With no task, it stops after setup and the briefing.
---

# dono

This session becomes the **owner of a pull request**. Ownership means the PR is the session's unit of work, and every piece of work related to it happens in that PR's worktree and branch, nowhere else.

## Ownership contract

For as long as this session is alive:

- **One worktree, one branch.** All work tied to the PR goes into the PR's `headRefName` branch, inside its worktree. Never edit that PR's files from the main worktree or from another branch's worktree.
- **Never switch branches inside that worktree.** If work for another PR shows up, that is another session or another `/dono`.
- **Check before editing.** Before the first `Edit`/`Write` of each work block, `git branch --show-current` must return the PR branch.
- **Never open a new PR** for the same subject. The PR already exists, and that is what the session takes care of.
- **Never commit or push without an explicit request from the user.** This holds even after the task succeeds: implement, report, wait for the request.
- **Never monitor CI.** The user turned that behavior off in `CLAUDE.local.md`. Only look at checks when asked.
- **Strict scope.** Execute the requested task, not what looks adjacent. Missing precondition means ask.

## Arguments

`/dono <pr> [task description]`

| Token | Rule |
|-------|------|
| `<pr>` (required) | First token. Accepts `123`, `#123`, a GitHub URL, or a branch name. |
| task description (optional) | Everything else in the prompt. Free-form. Without it, the skill only does setup plus briefing and stops. |

No `<pr>`: ask which PR and stop. Do not guess from the current branch.

## Flow

1. Resolve the PR.
2. Look for an existing worktree holding the PR branch.
3. Not found: create the worktree through the project's flow.
4. Enter the worktree and sync with the remote.
5. Load the PR context.
6. Report the ownership table.
7. Task present: execute it. No task: stop.

### 1. Resolve the PR

```bash
gh pr view <pr> --json number,title,url,state,isDraft,headRefName,baseRefName,isCrossRepository,author,labels,changedFiles
```

Blockers (stop and report, do not work around them):

- `state` other than `OPEN`: say the PR is `MERGED`/`CLOSED` and ask whether to own it anyway. Only continue on an explicit yes.
- `isCrossRepository` = `true`: the branch lives in the author's fork, not in `origin`. It cannot be owned through the normal worktree flow. Report and stop.

`isDraft` = `true` is not a blocker, it only goes into the report.

### 2. Does a worktree already exist?

Detection is **by branch**, never by directory name (the worktree may have been created under a different name):

```bash
git worktree list --porcelain | python3 -c "
import sys
path = None
for line in sys.stdin:
    line = line.rstrip('\n')
    if line.startswith('worktree '): path = line[9:]
    elif line == 'branch refs/heads/<HEAD_REF>': print(path)
"
```

Found: skip step 3 and go straight to step 4, entering with `EnterWorktree` using `path:` (never `name:`).

### 3. Create the worktree

The PR branch **already exists on the remote**. That changes the creation step compared to a fresh feature branch, but it does not remove the need for the project's environment setup (bundle, yarn, gitignored files, fixtures, assets).

Slug and path:

```bash
MAIN_WORKTREE="$(git worktree list --porcelain | head -1 | sed 's/worktree //')"
SLUG="pr-<number>"
WORKTREE_PATH="$MAIN_WORKTREE/.claude/worktrees/$SLUG"
```

**Path A, the project ships a `worktree-setup` skill.** `CLAUDE.md` requires creating worktrees through it, and it is what performs the environment setup. It always creates a fresh `worktree-<slug>` branch off a base, so the usage here is: base = the PR branch itself, then the session switches onto the real PR branch.

```
/worktree-setup pr-<number> <HEAD_REF>
```

Once setup finishes, already inside the worktree:

```bash
git fetch origin "<HEAD_REF>"
if git show-ref --verify --quiet "refs/heads/<HEAD_REF>"; then
  git switch "<HEAD_REF>"
else
  git switch -c "<HEAD_REF>" --track "origin/<HEAD_REF>"
fi
git branch -D "worktree-pr-<number>"
```

The `-D` on the throwaway branch is safe because it was born pointing exactly at `origin/<HEAD_REF>` and never received a commit; `worktree-setup` itself confirms this when `rev-list --count HEAD..origin/<base>` prints `0`. If that counter printed anything other than `0`, **delete nothing** and report, because the premise broke.

**Path B, project without a worktree skill.** Create it directly, already on the PR branch:

```bash
git -C "$MAIN_WORKTREE" fetch origin "<HEAD_REF>"
git -C "$MAIN_WORKTREE" worktree add --track -b "<HEAD_REF>" "$WORKTREE_PATH" "origin/<HEAD_REF>"
```

Then enter with `EnterWorktree` (`path:`) and run whatever environment setup the project documents. `--track` is correct here and does not contradict the rule against branches tracking a shared base: the upstream becomes `origin/<HEAD_REF>`, which is the branch's **own name**, not a shared branch.

### 4. Sync

In both paths, and also when the worktree already existed:

```bash
git fetch origin "<HEAD_REF>"
git rev-parse --abbrev-ref --symbolic-full-name @{u}     # must be origin/<HEAD_REF>
git status --short                                        # local dirt
git pull --ff-only
```

- Upstream missing or pointing elsewhere: `git branch --set-upstream-to=origin/<HEAD_REF>`.
- `git pull --ff-only` failed on divergence: **stop and report**. Do not rebase, do not merge, do not force.
- Dirty tree in a worktree that already existed: list the files and ask before touching anything. Another session's work may be sitting there.

### 5. PR context

Load this before writing any code:

```bash
gh pr view <number> --json title,body,labels,isDraft,baseRefName,reviewDecision
gh pr diff <number>
gh pr view <number> --json comments --jq '.comments[] | "\(.author.login): \(.body)"'
gh api "repos/{owner}/{repo}/pulls/<number>/comments" --jq '.[] | "\(.path):\(.line) \(.user.login): \(.body)"'
```

Reading the PR diff matters even when the task looks independent: an owner who rewrites what the PR already did is the easiest way to wreck the work.

### 6. Ownership report

Fixed format:

```
| PR | Branch | Base | Worktree | State |
|----|--------|------|----------|-------|
| #<n> <title> | <headRefName> | <baseRefName> | <path> (new or existing) | <OPEN/DRAFT>, <level with origin or N commits behind> |

Task: <one-line summary, or "none">
```

No task in the prompt: stop here, saying the session is ready to receive the demand.

### 7. Execute the task

With a task in the prompt, execute it directly, with no confirmation gate. The user already asked for execution by passing the description.

Single exception: the task admits different readings that materially change the work. Then use `AskUserQuestion` first, one question only, and move on.

While executing:

- Validate the description's premises against the code before implementing. Divergence between description and code: stop and report with evidence (`CLAUDE.md`).
- Project skills apply as usual. Bug with unknown cause: find the cause before proposing a fix — reproduce it, then narrow it down — instead of patching the symptom. Large demand with no shape: the project's shaping skill first, when it ships one.
- Tests only through the queue or runner the project documents, one run at a time. **Infrastructure** failure (database, migration, fixture, connection): stop and hand it back to the user with the exact message, without trying to fix the environment.
- No browser automation and no dev server unless the user asks.
- At the end: summarize what changed (files plus behavior), what was verified, and what was left out. No commit and no push until the user asks.

## When NOT to use

- The PR does not exist yet: this skill is about owning an open PR. A new branch is `/worktree-setup` plus `/pr`.
- Only reading or reviewing the PR, without working on it: `/soffner:self-review`, `/review-guide` or `gh pr diff` handle that without building a worktree.
- Delegating the demand to another background session: `/soffner:handoff`.
