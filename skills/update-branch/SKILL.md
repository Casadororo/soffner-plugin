---
name: update-branch
description: Use when the user asks to update the current branch with its base, bring the base in, or resolve conflicts against it (`atualiza a branch`, `traz a develop pra ca`, `merge da base`, `resolve os conflitos com a base`), or invokes `/update-branch`. Merges the base INTO the current branch and resolves conflicts by reasoning about intent, never by rebasing, never by merging the branch into the base, and never with a push. Never starts a merge on its own initiative.
---

# update-branch

Updates the **current branch** (the branch of this chat's context) with the changes of its **base**, by merging the base into the branch. Invoking it authorizes running the merge and resolving conflicts that fall into known patterns, plus reasoning through unambiguous code conflicts. **No push.**

```
/update-branch [base=<branch>]
```

With no argument the skill resolves the base from the PR, then from the project's `CLAUDE.md`.

## Scope and authorization

Invoking authorizes:

- Running `git merge origin/<base>` on the current branch.
- Resolving conflicts in the **known pattern classes** (see "Conflict resolution").
- Reasoning through and resolving **unambiguous** code conflicts.
- Closing the merge with `git merge --continue`, which creates the merge commit.

The skill **never**:

- Runs `git push`. It waits for an explicit request.
- Runs `git rebase` to escape a conflict.
- Merges the current branch **into** the base. The direction is always base first, current branch second.
- Uses `--no-verify`. The project's hooks run on the merge commit like on any other.

Stop and ask for human input when:

- The working tree is dirty.
- The base is ambiguous.
- Migrations diverge.
- A business-logic conflict is genuinely ambiguous.
- Any destructive database command falls outside the schema-only flow described here.

## Direction, and why it is the whole game

The operation is `git merge origin/<base>` **while on the current branch**. It brings the base into the branch. It does not carry the branch to the base, and it is not a rebase.

In this direction the sides are:

| Side | Stage | Flag | Is |
|---|---|---|---|
| ours | `:2:` | `--ours` | the **current branch**, the work of the PR |
| theirs | `:3:` | `--theirs` | **`origin/<base>`**, the base, the truth |

This is the opposite of a skill that merges a branch into an integration branch. Getting it backwards silently throws away either the base or the PR, so read the table before typing a flag.

Mental model: take the base as the new foundation and re-apply the PR's intent on top of it. The base wins on everything outside the PR's purpose. The PR's deliberate changes are preserved and repositioned over the current version of the base.

## Flow

### 1. Pre-flight

```bash
git status
git rev-parse --abbrev-ref HEAD
```

- **Clean working tree.** Staged, unstaged or untracked change means stop and ask. No automatic stash.
- **Merge already in progress.** `.git/MERGE_HEAD` exists means ask whether to continue (jump to step 4) or abort with `git merge --abort`.

Make sure history is complete, since a shallow clone produces `refusing to merge unrelated histories`:

```bash
test -f .git/shallow && git fetch --unshallow origin || git fetch origin
```

### 2. Resolve the base

In order, first one that answers wins:

1. The user passed `base=<branch>`.
2. The branch has a PR. The PR's base is the real base, no guessing needed:

   ```bash
   gh pr view --json number,baseRefName,headRefName
   ```

3. No PR yet. Try the project's integration branches, in the order its `CLAUDE.md` documents, and keep the one HEAD actually forked from:

   ```bash
   git merge-base --fork-point origin/<candidate> HEAD
   ```

   `--fork-point` depends on the reflog and comes back empty in a fresh clone or a fresh worktree. When it does, fall back to `git merge-base origin/<candidate> HEAD` and compare how far each candidate sits from HEAD.

4. Nothing documented. Use the repository's default branch:

   ```bash
   gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
   ```

Two candidates equally plausible means stop and ask. Picking the wrong base drags in commits that were never meant for this branch, and the merge commit makes that hard to unwind.

Update the base's remote ref:

```bash
git fetch origin <base>
```

### 3. Start the merge

**Fast path, PR open and the merge would be clean.** GitHub can do this server-side, no local checkout:

```bash
gh api "repos/{owner}/{repo}/pulls/<pr>/update-branch" -X PUT
```

That endpoint merges the base into the PR (it is a merge, not a rebase). A real conflict returns 422, which is the signal to fall into the local flow below. Do not fire it without a reason — a real conflict, or a fix the base already landed — since each call burns a CI run.

**Local flow:**

```bash
git merge origin/<base> --no-edit
```

No conflict means jump to step 5. Conflict means step 4.

### 4. Conflict resolution

List what is conflicted:

```bash
git status --short | grep -E '^(U|AA|DD|AU|UA|UD|DU|UU) '
```

#### 4.1 Framework by region, reasoning instead of a blind side

For each conflicted file or hunk:

- **(a) Only the base touched the region, the PR did not.** Keep the base (`--theirs`). The base is the truth.
- **(b) Only the PR touched the region, the base did not.** Keep the PR (`--ours`). It is what the PR delivers.
- **(c) Both touched different regions of the same file.** Git already auto-merged them. Keep both, nothing to do.
- **(d) Both touched the SAME region, a real conflict.** Reason from intent. What was the PR trying to do there? Re-express that intent over the current version of the base. Read both sides before deciding:

```bash
git show :2:<path>   # ours = current branch (PR)
git show :3:<path>   # theirs = base
```

The base wins on incidental, structural or refactor changes the PR did not make on purpose. The PR wins on its deliberate feature or fix. When both are deliberate and compatible, combine them.

After resolving each file: `git add <path>`.

#### 4.2 Known pattern classes

These are classes of file, not a fixed list of paths. Match the file to its class and apply the class's rule. The examples are the shape each class takes in a Rails project.

**Lockfiles** — `Gemfile.lock`, `yarn.lock`, `package-lock.json`, `pnpm-lock.yaml`, `Cargo.lock`, `poetry.lock`, `go.sum`, and nested ones under `vendor/`.

Never hand-merge a lockfile. Take the base side, then let the project's installer re-resolve it:

```bash
for f in $(git status --short | grep -E '^UU ' | awk '{print $2}' | grep -E '(Gemfile\.lock|yarn\.lock|package-lock\.json|pnpm-lock\.yaml|Cargo\.lock|poetry\.lock|go\.sum)$'); do
  git checkout --theirs "$f"
done
<install command the project documents>   # e.g. bundle install, yarn install --frozen-lockfile
git add <lockfiles>
```

Nested manifests need their own run, one per directory that has a manifest of its own (`vendor/vbus`, `vendor/vassis`, each workspace package).

Mandatory afterwards: if the project documents a dependency-bump review (v360 keeps it in `.claude/rules/gem-bumps.md`, changelog from the old version to the new plus a sweep of the callers), run it for every dependency whose version moved because of the base. A lockfile that merges cleanly still changes runtime behaviour.

**Generated schema** — `db/schema.rb`, `db/structure.sql`, a second schema file for a secondary database, any file a tool writes and no human edits.

Do not merge the text. Start from the base's schema and re-apply the branch's migrations:

```bash
git checkout origin/<base> -- db/schema.rb
<migrate command the project documents>   # e.g. bundle exec rails db:migrate
git add db/schema.rb
```

This touches the database. Follow the project's database rules (v360 keeps them in `.claude/rules/agent-behavior/database-operations.md`), confirm which environment and which database you are pointing at, and confirm with the user before touching it. If migrating fails, treat it as infrastructure and hand it back — do not try to repair the database alone.

**Divergent migrations** — two branches with a migration under the same timestamp prefix, or two migrations altering the same object.

Stop and ask. Renumbering or reordering a migration needs a human head, and getting it wrong breaks every environment that already ran the old order.

**Machine-regenerated artifacts** — test-selection manifests, coverage baselines, generated API clients, compiled assets, anything a cron or a CI job rewrites on a schedule.

Take the base, or regenerate with the project's command. There is no meaning in the PR's copy. In v360 this is the nightly cron's `.selective_tests/**/manifest.json`:

```bash
git checkout --theirs .selective_tests/manifest.json .selective_tests/vbus/manifest.json
git add .selective_tests/manifest.json .selective_tests/vbus/manifest.json
```

**Additive key files** — locale `.yml` and i18n JSON, enum lists, feature-flag registries, fixture indexes.

Combine the keys from both sides, base keys plus the PR's new keys. Never drop a side. A dropped locale key ships as a missing translation, and nothing in CI catches it.

**Changelogs and release notes** — keep both entries and follow the base's ordering. Never resolve by dropping one side's line.

### 5. Finish

Confirm nothing is still conflicted:

```bash
git status --short | grep -E '^(U|AA|DD|AU|UA|UD|DU|UU) '
```

Close the merge without opening an editor:

```bash
git -c core.editor=true merge --continue
```

If the conflicts touched code, run only the tests of the affected files, through the runner the project documents, never the whole suite:

```bash
set -o pipefail; <project test command> <affected file> 2>&1 | tee tmp/test-output.log
```

Infrastructure failure (database, fixtures, environment) goes back to the user with the exact message. Do not try to fix the environment.

**No push.** Wait for an explicit instruction.

### 6. Report

```
Merge <hash> — origin/<base> into <current branch>

| File | Class | Resolution |
|------|-------|------------|
| <path> | <lockfile / schema / artifact / keys / code> | <base, PR, combined, or regenerated> |

<N> commits ahead of origin/<current branch>. Not pushed.
```

Plus, below the table:

- For every logic conflict resolved by hand, the decision and why — which intent of the PR was preserved over the base.
- If a lockfile or a manifest moved, the result of the dependency-bump scan.
- Tests run and their outcome, or why none were run.

## Never

- NEVER rebase to escape a conflict.
- NEVER merge the current branch into the base. The direction is base into current branch.
- NEVER push or `--no-verify` without an explicit request.
- NEVER take a blind side in a real conflict (case d). Read both sides and reason from intent.
- NEVER revert a generated schema automatically without understanding the state of the database.
- NEVER close an update that moved a lockfile without the project's dependency-bump scan.

## When NOT to use

- **The branch is behind and there is no conflict in sight.** `git pull --ff-only` or the fast path in step 3 already does it.
- **Carrying the branch's work into the base.** That is the opposite direction, and it belongs to the project's merge or release flow.
- **Cleaning up history before review.** That is a rebase, and this skill never rebases.
