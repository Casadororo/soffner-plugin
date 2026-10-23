---
name: changelog-vdev
description: Use when the operator asks for the periodic changelog of vdev (changelog do vdev, monta o changelog do vdev), or invokes `/changelog-vdev`. vdev only, never the deck one too. Finds the last vdev changelog the operator posted in the arquitetura-v360 Slack channel, collects every PR merged into plugins/vdev or docs/vdev of v360-agents since it, drafts the next one in the same pt-BR format (one message by section) and posts it to Slack only after the operator's OK.
---

# changelog-vdev

The vdev changelog is periodic, so its start is always where the previous one stopped. The previous one lives in Slack, which makes Slack the only state: no file to keep, no date to type.

**Scope.** vdev only. The deck changelog is its own skill, `/soffner:changelog-deck`, and this one never collects, drafts, offers or posts it. They were one skill once, and asking for one changelog ended up posting both.

**Language.** These instructions are English. The changelog is **pt-BR with correct accents**, because it goes to the pt-BR team in #arquitetura-v360: the plugin's "content published elsewhere" exception. That is why the template below is pt-BR; do not translate it. What you print to the operator is English.

## Target

- Repo: `virtual360-io/v360-agents`, clone at `~/Documents/Github/v360-agents`, only `plugins/vdev` and `docs/vdev`.
- What counts: every PR whose merge touched those two paths, minus the `chore(versao)` bumps.
- Version: `version` in `plugins/vdev/.claude-plugin/plugin.json` on `origin/main`.
- Channel: `#arquitetura-v360` (`C0AJF3J99FW`).

## 1. Anchor on the previous changelog

Search Slack (`slack_search_public`, the channel is public) for the operator's newest vdev changelog in `C0AJF3J99FW`, sorted by timestamp: keywords `Changelog` `vdev`; the message starts with `:package: *Changelog do vdev`. Its title has the version range, and its `No forno` section lists the open PRs to follow up.

The anchor is the **post time** of that message. Everything merged after it is new; everything merged before it was already told.

- Never filter by PR number. Numbers are not merge order, and a number range drops the PRs that merged late.
- No previous changelog found: take the last 7 days and say so in the draft summary.
- Read the previous one whole before writing. It is the format, and its wording is the voice.

## 2. Collect

```bash
cd ~/Documents/Github/v360-agents && git fetch -q origin main
git log origin/main --since='<anchor>' --format='%h %ad %an | %s' --date=iso -- plugins/vdev docs/vdev | grep -v 'chore(versao)'
git show origin/main:plugins/vdev/.claude-plugin/plugin.json | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])'
git ls-tree --name-only origin/main plugins/vdev/skills/ | xargs -n1 basename
git ls-tree --name-only "$(git rev-list -1 --before='<anchor>' origin/main)" plugins/vdev/skills/ | xargs -n1 basename
gh pr list --state open --label VDev --json number,title,author,isDraft,createdAt
```

- The PR numbers are at the end of the merge subjects (`(#641)`). Read each with `gh pr view <n> --json title,author,body,files`.
- The two skill listings, compared, give the skills that came in and went out; a rename is one of each.
- A PR that came in and was reverted inside the period goes to `Entrou e saiu`, never to `Mudanças de comportamento`.
- Each PR in the previous `No forno`: `gh pr view <n> --json state,mergedAt`. Merged, closed without merge, still open; each outcome is one line.
- Names: `gh api users/<login> -q .name`, the login when the name is empty.

## 3. Write

Same voice as the previous changelog. On top of it:

- What the person sees or types, never a file or a function. A command, key, flag, label or path the reader needs to act stays, in backticks.
- Why, when the PR has an incident behind it ("o v360#49601 saiu sem ela, e o CI foi pulado sem nenhum aviso").
- Positive and concrete. "Parou de travar" was rewritten as "uma experiência mais fluida" with the numbers from the PR: say what got better, not what was broken.
- No `--`, em or en dash; no marketing words; none of the fingerprints in `/soffner:polish-text`.
- A PR that changes nothing anyone sees (docs only, CI) is counted, never described.

One message. A section with nothing in it is dropped whole.

```
:package: **Changelog do vdev: semana de [DD] a [DD/MM] ([versão do anterior] → [versão atual])**
Entraram [N] PRs. [Nenhuma skill entrou ou saiu (seguem 22). | Entrou a X e saiu a Y (agora são 23).] Os destaques: [os dois ou três maiores, numa frase].

:new: **Skills novas e removidas**
• **[skill]**: [o que faz e quando usar, ou por que saiu e o que a substitui]. [#NNN](https://github.com/virtual360-io/v360-agents/pull/NNN) · [Nome]

:wrench: **Mudanças de comportamento**
• **[skill]**: [o que muda para quem usa e, se houve, o motivo]. [#NNN](https://github.com/virtual360-io/v360-agents/pull/NNN) · [Nome]

:rewind: **Entrou e saiu**
• **[skill]**: [o que o #A fez, por que o #B reverteu e onde a ideia ficou]. · [Nome]

:keyboard: **Para quem digita**
• [Nenhum comando mudou de nome. | O comando renomeado ou removido.] [Comando novo: `/vdev:...`.]

:hourglass_flowing_sand: **No forno**
• **[skill]**: [o que os PRs abertos fazem, cada número linkado]. · [Nome]
• Do forno do changelog anterior: [o que entrou, o que fechou sem merge e o que isso significa para quem usa].

:bust_in_silhouette: **Quem mexeu na semana**
• [Nome]: [N] PRs (#a, #b)
```

- One bullet per change, not per PR: a PR that changes two things gets two bullets.
- Title: `semana de DD a DD/MM` when the period fits in one week, `de DD/MM a DD/MM` otherwise.
- When the anchor is older than this week, this week is the body and the earlier days go in one more section before `Quem mexeu`, shorter: `:calendar: **Entre o último changelog e esta semana ([DD] a [DD/MM], [versão] → [versão])**`.

## 4. Gate and post

Save the draft to `~/.cache/soffner-changelog/vdev-<version>/changelog.md`, the message in its own fence (no language, so `:emoji:` stays literal). Print the same message in the chat.

Then **one `AskUserQuestion`**:

- `Enviar como está (Recommended)`
- `Ajustar antes`: rewrite the same file and ask again.
- `Salvar como rascunho no Slack` (`slack_send_message_draft`).
- `Só o rascunho`: stop; the operator posts by hand.

Posting goes through the Slack MCP:

- The `message` takes **standard markdown**: `**bold**`, `_italic_`, `[text](url)`. A single `*bold*` comes out italic, which is what broke the 14/10 headings.
- `slack_send_message` to `C0AJF3J99FW`, the message as drafted.
- Never add the "O envio foi feito usando Claude" line: Slack appends it.

## 5. Report

The permalink of the message posted, what the changelog covered (period, PRs, version), and anything left out with the reason.

## When NOT to use

- The deck changelog: `/soffner:changelog-deck`.
- A one-off announcement of a single feature: `/vdev:announcement`.
- Polishing a changelog the operator already wrote: `/soffner:polish-text`.
