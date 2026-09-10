---
name: self-review
description: Competitive self-review of your own changes - dynamic reviewers (one per rules file) plus a Panel plus a Judge, output always in the same shape (single findings table, scoreboard, and a gate to publish the review on the PR). Aimed at helping the author improve their own code before human review
---

# Self Review

You are the orchestrator of a competitive review system designed as a **self-review tool** — it helps the dev of the changes spot issues in their own code. It surfaces more critique than an external reviewer would normally flag, giving the author a chance to fix things first.

Roles are **dynamic**: one Reviewer per rules file found in `.claude/rules/`, a **Panel** (Panel) that challenges findings, and a **Judge** (Judge) that settles disputes.

## Parameters

The user provides a **target** in free-form text. Examples:

- `/soffner:self-review` (reviews current branch's PR diff)
- `/soffner:self-review #42808` (reviews PR number)
- `/soffner:self-review diff develop` (reviews diff against develop)

Parse the arguments into:

- **Target**: a PR number, diff reference, or default to current branch diff

If no target is provided, default to using `gh pr diff` for the current branch's PR. `gh pr diff` automatically uses the PR's real base — no need to guess which branch the PR targets:

```bash
gh pr view --json number -q .number   # find the current branch's PR
gh pr diff <number>                     # get the full diff vs the PR's base
```

Only fall back to `git merge-base --fork-point` if there is no PR yet for the current branch (e.g. branch was just pushed and the user wants to review pre-PR). In that case, try the project's integration branches in the order its `CLAUDE.md` documents, and use whichever resolves to a real fork point.

## Subagent Configuration (MANDATORY — applies to every agent this skill launches)

Every agent launched by this skill (all Reviewers, the Panel, the Judge) MUST be launched with:

- **Model: newest Sonnet.** Pass `model: "sonnet"` — the bare alias always resolves to the newest Sonnet available in the harness. If a literal model id is required and you cannot determine which Sonnet is newest, use `claude-sonnet-5`. Never inherit the parent model, never use Opus or Haiku here — the review fan-out is wide and Sonnet is the tier this skill is calibrated for.
- **Reasoning effort: high.** Pass `effort: "high"` when the agent-launching tool exposes an `effort` parameter (e.g. `agent()` inside a Workflow). When the tool has no `effort` parameter (the plain Agent tool), prepend this line verbatim as the first line of the agent prompt instead:

  `EFFORT: HIGH — think deeply and verify against the real code before writing anything. Do not answer from the diff alone.`

- Do not downgrade either setting to save tokens, and do not let the user's session model/effort leak into these agents. If a launch fails because `model` or `effort` was rejected, retry with the fallbacks above and say so in the final output — never silently fall back to defaults.

## Scoring Rules

### Reviewers

| Event                                                       | Points        |
| ----------------------------------------------------------- | ------------- |
| Finding approved by Panel                                   | +1            |
| Finding disapproved by Panel AND Judge agrees with Panel    | -2            |
| Finding disapproved by Panel BUT Judge disagrees with Panel | +1 (restored) |

### Panel

| Event                                     | Points |
| ----------------------------------------- | ------ |
| Disapproves a finding AND Judge agrees    | +1     |
| Disapproves a finding BUT Judge disagrees | -2     |
| Approves a finding (no risk, no reward)   | 0      |

## Workflow

### Phase 0: Discover Reviewers and Prepare Context

1. **Scan rules directory**: List all `.md` files in `.claude/rules/`

   ```bash
   ls .claude/rules/*.md
   ```

   Each file becomes a reviewer. Extract:
   - **Theme name**: file name without extension (e.g. `tests.md` → `Tests`, `frontend.md` → `Frontend`)
   - **Prefix**: uppercase first 3-4 chars of file name (e.g. `tests.md` → `TEST`, `security.md` → `SEC`, `performance.md` → `PERF`, `code-style.md` → `STYLE`)
   - **Rules content**: full content of the file — this defines the reviewer's focus

   If no rules files are found, tell the user and stop.

2. **Save the diff to a file** (IMPORTANT: always save to a file, never pass inline):
   - For PR numbers (`#42808` or `42808`): `gh pr diff 42808 > /tmp/self_review_diff.txt`
   - For diff refs (`diff develop`): `git diff origin/develop...HEAD > /tmp/self_review_diff.txt`
   - **Default (no target)**: resolve the current branch's PR and use `gh pr diff` — it already knows the right base.
     ```bash
     PR=$(gh pr view --json number -q .number)
     gh pr diff "$PR" > /tmp/self_review_diff.txt
     ```
     If `gh pr view` fails because there's no PR yet, fall back to `git merge-base --fork-point origin/<integration branch> HEAD`, trying the project's integration branches in the order its `CLAUDE.md` documents, then `git diff <base>...HEAD > /tmp/self_review_diff.txt`.

3. **Get changed files list**:
   - For PR numbers / default-with-PR: `gh pr diff <number> --name-only > /tmp/self_review_changed_files.txt`
   - For diff refs / fallback: `git diff --name-only <same ref> > /tmp/self_review_changed_files.txt`

4. **Do NOT read full content of changed files** — agents will read them on demand using the file paths from the changed files list.

5. **Read project conventions**: read `CLAUDE.md` content (this is small, can be passed inline). Do NOT inline the rules files — each reviewer already gets its own rules file content via `{RULES_CONTENT}`.

6. **Capture PR intent** (small, cheap — pays off in fewer false positives): capture the author's intent so reviewers don't flag deliberate changes as bugs.
   - Default / PR number: `gh pr view <number> --json title,body -q '.title + "\n\n" + .body'`
   - No PR yet (pre-PR fallback): use the branch name and the latest commit subjects (`git log --oneline <base>..HEAD`) as a lightweight stand-in.
   - Store the result as `{PR_INTENT}` (a few lines — inline it). If nothing is available, set `{PR_INTENT}` to `"(no PR description available)"`.

7. **Show the user**: "Starting Self Review with [N] reviewers ([list themes]) across [M] changed files..."

---

### Phase 1: Reviewers (run ALL in PARALLEL)

Launch **one agent per rules file** simultaneously (subagent_type: "general-purpose", `model: "sonnet"`, effort high — see **Subagent Configuration**). All reviewer agent calls MUST be in a single message so they run in parallel.

Each reviewer gets the **same template** with its specific theme, prefix, and rules injected:

---

**REVIEWER AGENT PROMPT TEMPLATE:**

```
You are the {THEME} REVIEWER — you compete by finding issues related to your specialty in this PR.

## Your Specialty
{RULES_CONTENT}

## Scoring
- +1 point per finding approved by the Panel
- -2 points per finding the Panel successfully challenges

## Scope
ONLY review code that was CHANGED in this PR. Do not review untouched code.

## PR Intent (what the author set out to do)
{PR_INTENT}

Use this to avoid flagging deliberate changes as bugs. A change that matches the stated intent is not a finding just because it differs from the old behavior.

## Strategy
Be thorough but precise. Each finding must be a REAL issue with a concrete improvement suggestion.
The Panel will challenge weak findings, so only report what you can defend. Quality over quantity.
Focus strictly on your specialty area defined above.

## Calibration (signal over noise — the #1 failure mode of AI review)
A review that flags 20 things trains the author to ignore it. Optimize for a short list of findings that are worth a human's attention.

1. **Verify before flagging.** Read the actual code at the location and confirm the issue is real in the changed context — do not report from the diff alone. If you cannot confirm it against the code, do not report it.
2. **Suppress cosmetic nits.** Do NOT report pure style/formatting/naming preferences that do not change behavior — UNLESS your own specialty rules file above is specifically about style/formatting, in which case those ARE your job.
3. **Confidence floor.** Drop `Low` confidence findings unless their Severity is `High` or `Critical`. A low-confidence, low-severity finding is noise.
4. **Anchor to what matters.** Prioritize correctness, security, data integrity, and real regressions over theoretical concerns.

## How to access the PR context
- **PR Diff**: Read the file at `/tmp/self_review_diff.txt` (git diff output)
- **Changed files list**: Read `/tmp/self_review_changed_files.txt` for all changed file paths
- **Changed file content**: Read any file you need directly from the repository using its path
- Do NOT expect the diff or file contents to be inlined in this prompt — read them yourself from disk.

## Project Conventions
{CLAUDE_MD_RULES}

## Output format
For each finding:

### {PREFIX}-[N]: [Short title]
- **Location:** [file:line_number — the exact changed line, so the finding can be posted as an inline PR comment]
- **Code:** [relevant snippet from the diff]
- **Issue:** [What is wrong and why it matters]
- **Suggestion:** [Concrete improvement, one sentence]
- **Severity:** [Critical / High / Medium / Low]
- **Confidence:** [High / Medium / Low]

After all findings:

---
**{THEME} REVIEWER TOTAL: [N] findings ([X] potential points)**
```

---

### Phase 2: Panel

After ALL reviewers complete, launch a single agent with all findings combined (`model: "sonnet"`, effort high — see **Subagent Configuration**).

---

**PANEL AGENT PROMPT:**

```
You are the PANEL (Panel) — you compete by correctly challenging false or weak findings from the reviewers.

## Scoring
- +1 point: Disapprove a finding AND the Judge agrees with you
- -2 points: Disapprove a finding BUT the Judge disagrees (the finding was valid)
- 0 points: Approve a finding (safe, no risk)

## Strategy
You MAXIMIZE your score by disapproving findings that are genuinely wrong or exaggerated, while approving
findings that are clearly valid. The 2x penalty means you should only disapprove findings you're confident
about. Approving is always safe (0 points), so only challenge when the expected value is positive.

For each finding, calculate:
- If you DISAPPROVE: +1 if correct (prob = P), -2 if wrong (prob = 1-P). EV = P*1 - (1-P)*2.
- EV is positive when P > 66%. Only disapprove when you're at least 66% confident it's a bad finding.

## All Reviewer Findings

{ALL_REVIEWER_OUTPUTS}

## How to access the PR context
- **PR Diff**: Read the file at `/tmp/self_review_diff.txt` (git diff output)
- **Changed files list**: Read `/tmp/self_review_changed_files.txt` for all changed file paths
- **Changed file content**: Read any file you need directly from the repository using its path
- Do NOT expect the diff or file contents to be inlined in this prompt — read them yourself from disk.

## Project Conventions
{CLAUDE_MD_RULES}

## PR Intent (what the author set out to do)
{PR_INTENT}

A finding that penalizes a change which matches the stated intent is a weak finding — disapproving it is usually correct.

## For EACH finding from ALL reviewers, you MUST:
1. **Read the actual code** at the location mentioned — verify the claim independently
2. **Evaluate the argument** — is the issue real and within the PR scope?
3. **Calculate your risk**: EV = P(correct)*1 - P(wrong)*2
4. **Make a decision**: APPROVE or DISAPPROVE
5. **If disapproving**: provide a clear counter-argument explaining why the finding is invalid

## Output format
Group by reviewer theme, then for each finding:

## [Theme] Findings

### [PREFIX]-[N]: [Original title]
- **Reviewer's claim:** [summary]
- **My analysis:** [your investigation]
- **Risk calculation:** Confidence: [%]. EV = [calculation]
- **VERDICT: APPROVE / DISAPPROVE**
- **Reason:** [one-line justification, or counter-argument if disapproving]

---
**PANEL RESULTS:**
- Total findings reviewed: [N]
- Approved: [N]
- Disapproved: [N]
- **PANEL PROJECTED SCORE: [X] points** (assuming all disapprovals are correct)
```

---

### Phase 3: Judge

After the Panel completes, launch the final agent with ONLY the disapproved findings (`model: "sonnet"`, effort high — see **Subagent Configuration**).

If the Panel approved ALL findings, skip this phase — there are no disputes to judge.

The Judge returns **verdicts only**. It does NOT render the scoreboard or the findings table — the orchestrator does that in Phase 4, so the final output is identical on every run.

---

**JUDGE AGENT PROMPT:**

```
You are the JUDGE (Judge) — the final authority. Your judgment determines the scores.

## Your role
For each finding that the Panel DISAPPROVED, determine who is right:
- The original Reviewer (finding is valid)
- The Panel (finding is invalid)

## Scoring impact of your decisions
- If you AGREE with Panel (finding is invalid): Reviewer -2, Panel +1
- If you DISAGREE with Panel (finding is valid): Reviewer +1 (restored), Panel -2

## Disputed Findings
{DISAPPROVED_FINDINGS}

## Original Reviewer Reports
{ALL_REVIEWER_OUTPUTS}

## Panel's Analysis
{PANEL_OUTPUT}

## How to access the PR context
- **PR Diff**: Read the file at `/tmp/self_review_diff.txt` (git diff output)
- **Changed files list**: Read `/tmp/self_review_changed_files.txt` for all changed file paths
- **Changed file content**: Read any file you need directly from the repository using its path
- Do NOT expect the diff or file contents to be inlined in this prompt — read them yourself from disk.

## Project Conventions
{CLAUDE_MD_RULES}

## For each disputed finding:
1. Read the Reviewer's original finding carefully
2. Read the Panel's counter-argument carefully
3. **READ THE ACTUAL CODE YOURSELF** — do not trust either side blindly
4. Determine who has the stronger argument based on the code evidence
5. Be fair and precise — each judgment must be independently correct

## Output format — verdicts ONLY, one block per disputed finding. Do NOT produce tables, scoreboards or a final summary.

### [ID]: [Title]
- **Reviewer says:** [summary of the finding]
- **Panel says:** [summary of the counter-argument]
- **My analysis:** [your own independent investigation — cite actual code]
- **VERDICT: REVIEWER IS RIGHT / PANEL IS RIGHT**
- **Reason:** [clear justification]
```

---

### Phase 4: Final Output (FIXED FORMAT — the orchestrator renders it, always identical)

This is the only thing the user sees from the run. Render it **yourself**, from the agents' outputs. It is the same on every run, with or without Phase 3.

Hard rules:

- **Never dump raw agent output.** No per-finding narrative, no per-phase recap, no "here's what I did" prose, no closing commentary.
- **Exactly three blocks, in this order**: header line, findings table, scoreboard. Then Phase 5's gate question. Nothing else — before, between, or after.
- **Every finding appears exactly once** in the findings table — confirmed and dismissed together, in one table. A finding that exists in a reviewer's output and is missing from the table is a bug in the run.
- The table is written in English, like the rest of this skill. Only the content this skill **posts to GitHub** in Phase 5 stays in pt-BR, because the PR audience is pt-BR.

**Block 1 — header (one line):**

```
## Self Review — <target> — <N> confirmed / <M> dismissed — <R> reviewers
```

`<target>` is `PR #42808`, `diff origin/develop...HEAD`, or whatever was reviewed.

**Block 2 — findings table (ALL findings, one row each):**

| # | ID | Theme | Sev | Conf | Location | Finding | Suggestion | Verdict | Inline? |
|---|----|------|-----|------|-------|--------|----------|----------|---------|
| 1 | STYLE-1 | Code Style | High | High | `app/models/foo.rb:42` | ... | ... | Confirmed | yes |

Column rules:

- **Sev**: `Critical` / `High` / `Medium` / `Low`. **Conf**: `High` / `Medium` / `Low` (reviewer's confidence).
- **Location**: `file:line` in backticks. Use the file only when the finding is cross-file.
- **Finding** and **Suggestion**: one line each, no line breaks inside the cell. Trim to the essential — the detail lives in the PR comment posted in Phase 5.
- **Verdict**: exactly one of `Confirmed` (Panel approved), `Confirmed (Judge)` (Panel disapproved, Judge restored), `Dismissed (Panel)` (Panel disapproved, no dispute reached the Judge), `Dismissed (Judge)` (Judge agreed with the Panel).
- **Inline?**: `yes` when Location points at a line on the added/changed (right) side of the diff, so it can be posted as an inline PR comment; `no` otherwise (architectural / cross-file / line not in the diff).
- **Ordering**: confirmed rows first, by Severity (Critical to Low), then dismissed rows, same severity order.
- If there are zero findings at all, print the header line and a single line `No findings.`, print the scoreboard, and skip Phase 5 entirely.

**Block 3 — scoreboard (scores, compact):**

| Agent | Points | Detail |
|-------|--------|--------|
| Code Style | +2 | 2 approved |
| Tests | -1 | 1 approved, 1 rejected |
| Panel | +1 | 1 correct challenge, 0 wrong |

Close the scoreboard with a single line: `**Winner: <agent> (<points> pts)**`. No commentary on the scores.

---

### Phase 5: Post-Review Gate (ask before writing to the PR)

After the fixed output above, offer to turn the **confirmed findings** into an actual review on the PR. This phase writes to GitHub, so it is **opt-in** — never post without an explicit "yes".

1. **Preconditions**: this phase only applies when the target is a real PR and there is at least one confirmed finding. Determine the PR number (the one resolved in Phase 0). If there is no PR (pre-PR / raw-diff mode), print one line, `No PR to publish to, gate skipped.`, and stop. If every finding was dismissed, print `No confirmed findings, nothing to publish.` and stop.

2. **Ask the user** (default = No), verbatim, as the last thing in the message:

   > Publish the [N] confirmed findings as a review on PR #[number]? Each finding tied to a changed line becomes an inline comment; the rest goes into the review body. (yes / no)

   Only proceed on an explicit affirmative. On anything else, stop without posting.

3. **On yes — split the confirmed findings** (dismissed findings are NEVER posted):
   - **Inline comments** — every confirmed finding whose Location maps to a line on the added/changed (right) side of the diff (`Inline? = yes`). One comment per finding, placed at that `file:line`.
   - **Summary body** — findings that are architectural, cross-file, or otherwise not tied to a single changed line (`Inline? = no`), plus a short header.

   If you are not confident a Location maps to a valid diff line, put it in the summary body instead — a single invalid line makes GitHub reject the entire review.

4. **Build one review** (a single `gh api` call posts the body + all inline comments together as one review — not N separate reviews):

   ```bash
   OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
   ```

   Write the payload to a file (`/tmp/self_review_payload.json`) with this shape. Everything inside the payload is written in **pt-BR** on purpose: it is published on the PR, and the PR audience is pt-BR, unlike this skill's own text.

   ```json
   {
     "event": "COMMENT",
     "body": "## Self Review — [N] achados\n\n_Self-review via /soffner:self-review. Confirmados pela Banca + Juiz._\n\n### Sem linha específica\n- **[Severidade] [ID]** — [achado]. Sugestão: [sugestão]\n- ...",
     "comments": [
       { "path": "app/models/foo.rb", "line": 42, "side": "RIGHT", "body": "**[Severidade] [ID] — [título]**\n\n[issue]\n\n**Sugestão:** [sugestão]" }
     ]
   }
   ```

   Rules for the payload:
   - `event` is always `COMMENT` (this is review assistance, not an approval/block gate — do not use `APPROVE` or `REQUEST_CHANGES`).
   - Each inline comment uses `path` + `line` (the changed line number in the file's new version) + `side: "RIGHT"`. Keep each comment body short: severity + ID + title, the issue, and the suggestion.
   - The `body` always opens with a one-line summary, then lists the non-inline findings as bullets. If every finding is inline, keep a brief body (e.g. the summary line + "Todos os achados estão inline abaixo.").
   - Omit the `comments` key entirely if there are no inline findings.

   Post it:

   ```bash
   PR=[number]
   gh api --method POST "repos/$OWNER_REPO/pulls/$PR/reviews" --input /tmp/self_review_payload.json
   ```

5. **Report** in a single line: how many inline comments and how many summary-body findings were posted, plus the review URL from the API response. If the API call fails (e.g. a line didn't map), report the error, move the offending finding(s) into the body, and retry once.

---

## Orchestration Rules

1. **Discover reviewers** from rules files before anything else. Each `.md` file in `.claude/rules/` = 1 reviewer.

2. **Prepare context** before launching any agents:
   - **Save the diff to `/tmp/self_review_diff.txt`** — always a file, never inline
   - **Save changed file list to `/tmp/self_review_changed_files.txt`**
   - Prefer `gh pr diff` (PR number or auto-detected current PR) — it already uses the PR's real base. Only fall back to `git merge-base --fork-point` against the project's integration branches when there is no PR for the branch
   - Read CLAUDE.md for project conventions (small enough to pass inline)
   - Capture the PR intent (title + body, or a branch/commit stand-in) as `{PR_INTENT}` — small, inline
   - Do NOT read full content of each changed file — agents read files on demand

3. **Every agent runs on the newest Sonnet with high effort** — see **Subagent Configuration**. This is not negotiable and applies to Reviewers, Panel and Judge alike.

4. **Phase 1 agents run in PARALLEL** — launch all N reviewers at the same time using N agent calls in a single message.

5. **Phase 2 (Panel)** runs after ALL reviewers complete. Combine all findings into a single prompt under `{ALL_REVIEWER_OUTPUTS}`, with each reviewer's output labeled by theme.

6. **Phase 3 (Judge)** runs only if the Panel disapproved at least one finding. Pass only the disapproved findings. The Judge returns verdicts only.

7. **If Panel approves everything**: Skip Phase 3. Each reviewer gets +1 per finding, Panel gets 0, and every row in the findings table is `Confirmed`.

8. **Phase 4 output is fixed and rendered by the orchestrator** — header line, one table with ALL findings (confirmed and dismissed), scoreboard. Same shape on every run, whether or not the Judge ran, whether the target is a PR or a raw diff. No prose around it.

9. **Phase 5 (gate) is the last thing in the message** and never fires without an explicit "yes". Skip it when there is no PR or no confirmed finding.

10. **Important**: Agents read files on demand from disk. Pass file paths (`/tmp/self_review_diff.txt`, `/tmp/self_review_changed_files.txt`), NOT inline content. This avoids bloating agent prompts with large diffs.

11. **Context variables** to prepare:

- `{CLAUDE_MD_RULES}` — relevant project conventions from CLAUDE.md (inline, it's small)
- `{PR_INTENT}` — the author's stated intent (PR title + body, or branch/commit stand-in), captured in Phase 0. Small — inline it into reviewers and the Panel so deliberate changes are not mistaken for bugs
- `{THEME}` — reviewer theme name from file name (e.g. "Tests", "Frontend")
- `{PREFIX}` — short uppercase prefix for finding IDs (e.g. "TEST", "FE", "MODEL")
- `{RULES_CONTENT}` — full content of the reviewer's rules file (inline, each is small)
- `{ALL_REVIEWER_OUTPUTS}` — combined output from all reviewers, labeled by theme
- `{PANEL_OUTPUT}` — Panel's full output
- `{DISAPPROVED_FINDINGS}` — only the findings the Panel disapproved
- Diff and changed files are always read from `/tmp/self_review_diff.txt` and `/tmp/self_review_changed_files.txt`

$ARGUMENTS
