---
name: changelog
description: Use when the operator asks for the periodic changelog of deck or vdev (changelog do deck, changelog do vdev, monta o changelog da semana), or invokes `/changelog`. Finds the last changelog the operator posted in the arquitetura-v360 Slack channel, collects everything merged since it, drafts the next one in the same pt-BR format (deck as an announcement with the changelog PR by PR and the prints in the thread, vdev as one message by section) and posts it to Slack only after the operator's OK.
---

# changelog

The changelog is periodic, so its start is always where the previous one stopped. The previous one lives in Slack, which makes Slack the only state: no file to keep, no date to type.

**Language.** These instructions are English. The changelog is **pt-BR with correct accents**, because it goes to the pt-BR team in #arquitetura-v360: the plugin's "content published elsewhere" exception. That is why the templates below are pt-BR; do not translate them. What you print to the operator is English.

## Arguments

| Invocation | Does |
|---|---|
| `/changelog` | deck and vdev, one after the other, one gate for both |
| `/changelog deck` | deck only |
| `/changelog vdev` | vdev only |

## Targets

| | deck | vdev |
|---|---|---|
| Repo | `virtual360-io/deck`, clone at `~/Documents/Github/deck` | `virtual360-io/v360-agents`, clone at `~/Documents/Github/v360-agents`, only `plugins/vdev` and `docs/vdev` |
| What counts | every PR merged into `main` | every PR whose merge touched those two paths, minus the `chore(versao)` bumps |
| Version | the newest tag after `git fetch --tags` (`v0.2.46` is published as `0.2.46`) | `version` in `plugins/vdev/.claude-plugin/plugin.json` on `origin/main` |
| Prints | `docs/*.png` that the PR changed | none |
| Format | announcement in the channel, changelog PR by PR in its thread | one message by section |

Both go to `#arquitetura-v360` (`C0AJF3J99FW`).

## 1. Anchor on the previous changelog

Search Slack (`slack_search_public`, the channel is public) for the operator's newest changelog of the target in `C0AJF3J99FW`, sorted by timestamp:

- **deck**: keywords `deck` `changelog`; the parent starts with `:claude-ai-icon: *deck*`. Read its thread: the first reply says how many PRs, which ones and the published version.
- **vdev**: keywords `Changelog` `vdev`; the message starts with `:package: *Changelog do vdev`. Its title has the version range, and its `No forno` section lists the open PRs to follow up.

The anchor is the **post time** of that message. Everything merged after it is new; everything merged before it was already told.

- Never filter by PR number. Numbers are not merge order: deck #57 and #58 merged three days after #59, which closed the 16/10 changelog, and a number range would drop them.
- No previous changelog found: take the last 7 days and say so in the draft summary.
- Read the previous one whole before writing. It is the format, and its wording is the voice.

## 2. Collect

### deck

```bash
cd ~/Documents/Github/deck && git fetch -q --tags origin
gh pr list --state merged --base main --limit 100 \
  --json number,title,author,mergedAt,files \
  -q '.[] | select(.mergedAt > "<anchor, ISO UTC>") | "#\(.number) \(.mergedAt) \(.author.login) \(.title) | \([.files[].path | select(startswith("docs/"))] | join(" "))"'
git tag --sort=-v:refname | head -1
```

Then `gh pr view <n> --json body` for each one. `Descrição` and `Motivação` say what changed and why; translate them into what the person sees on screen. Check the newest PR is inside the newest tag (`git merge-base --is-ancestor <merge sha> <tag>`); when it is not, the release is still building, so say "a versão publicada é a X" for the tag you have and leave the rest for the next changelog.

Prints: `git show origin/main:docs/<name>.png > <draft dir>/deck-<pr>-<slug>.png`. They carry demonstration data, which is why they may be published: never a capture of the operator's own screen. **Look at each one** before using it; a print that does not show what its reply says (an empty pane, an old layout) is reported to the operator, not published.

The parent message takes one image, and a Slack attachment is one file, so stack the two or three prints that best show the headline:

```bash
python3 -I - <<'EOF'
from PIL import Image, ImageDraw
BG = (21, 24, 30)  # the deck's background; the prints have transparent rounded corners
def clean(f):
    im = Image.open(f).convert('RGB'); w, h = im.size
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]: ImageDraw.floodfill(im, xy, BG, thresh=150)
    return im
ims = [clean(f) for f in ['<first>.png', '<second>.png']]; gap = 24
out = Image.new('RGB', (max(i.width for i in ims), sum(i.height for i in ims) + gap * (len(ims) - 1)), BG)
y = 0
for i in ims: out.paste(i, (0, y)); y += i.height + gap
out.save('<draft dir>/deck-anuncio.png', optimize=True)
EOF
```

### vdev

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

### deck

The parent is an announcement, so nobody has to read a changelog to know what is new. The thread is the changelog.

Parent, with `deck-anuncio.png`:

```
:claude-ai-icon: **deck**: [a maior novidade, e a segunda, numa linha]

Pessoal, saiu mais uma leva de melhorias no deck desde o último changelog. A maior novidade [é a/são as] [X]: agora dá para [o que a pessoa faz agora, numa frase].

**O que mudou:**
• [uma linha por novidade, do que a pessoa vê]
E [menos ruído na aba X / mais fluido]: [as correções pequenas numa frase só].

Para atualizar: `deck update`. Quem ainda não tem, a instalação está no README do [virtual360-io/deck](https://github.com/virtual360-io/deck).

O changelog, PR a PR e com prints, está na thread. Feedback e bugs, respondam por aqui! :raised_hands:
```

Thread, in this order:

```
**Changelog**: [N] PRs na main, [os números, em faixas: #57, #58 e do #60 ao #68] ([K] só de documentação ou CI), e a versão publicada é a [X.Y.Z].
```

```
**[A novidade, como título]** (#[NN])
[Como era, como ficou e o detalhe para usar: a tecla, o comando, o arquivo. No print, o que olhar.]
```

- One reply per novelty, with its print attached when the PR changed one. A second print for the same reply goes in the next reply, image only.
- Small fixes share one reply, `**Menos ruído na aba [X]** (#a, #b, #c)`, one bullet each, each ending in `(#n)`.
- A PR by someone other than the operator ends its reply with `· [Nome]`.

### vdev

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

Save the draft to `~/.cache/soffner-changelog/<target>-<version>/`: `changelog.md` with each Slack message in its own fence (no language, so `:emoji:` stays literal), plus the images. Print the same messages in the chat, and next to each thread reply the image it carries.

Then **one `AskUserQuestion`** for everything drafted:

- `Enviar como está (Recommended)`
- `Ajustar antes`: rewrite the same files and ask again.
- `Só o rascunho`: stop; the operator posts by hand.
- vdev only: `Salvar como rascunho no Slack` (`slack_send_message_draft`). A deck thread with images cannot be a draft.

Posting goes through the Slack MCP:

- The `message` and `initial_comment` take **standard markdown**: `**bold**`, `_italic_`, `[text](url)`. A single `*bold*` comes out italic, which is what broke the 14/10 headings.
- Text only: `slack_send_message`. With an image: `slack_get_file_upload_url` (filename, byte size, an `alt_txt` that describes the print), then `curl -sS -w '%{http_code}' -X POST "<upload url>" -H 'Content-Type: image/png' --data-binary @<file>`, then `slack_complete_file_upload` with the text as `initial_comment` and `thread_ts` for a reply. An HTTP 500 from the upload is retried once on the same URL.
- After the parent, `slack_read_channel` (`limit` 1, `response_format` detailed) gives its `ts`: the concise format omits it. Every reply goes with that `thread_ts`, one at a time, in the order of the draft.
- At the end, `slack_read_thread` on the parent and check every reply is there, in order, with its image.
- Never add the "O envio foi feito usando Claude" line: Slack appends it.

## 5. Report

The permalink of each message posted, what the changelog covered (period, PRs, version), and anything left out with the reason (a print that did not match, a release still building).

## When NOT to use

- A one-off announcement of a single feature: `/soffner:announcement`.
- Polishing a changelog the operator already wrote: `/soffner:polish-text`.
