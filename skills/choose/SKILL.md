---
name: choose
description: Use when the operator has to pick among several alternatives (designs, screens, prototypes, features, approaches, wordings) and should choose and comment on all of them in one pass instead of answering one question per message, when they ask for an HTML page of options to select from, or invoke `/choose`. Builds one self-contained HTML page with the options in groups (pick one or pick many), a real picture or a code block for each, a note per option and one at the end, and a button that copies the choices as text to paste back into the chat, then opens it in the operator's browser. Runs in rounds, the next one showing how the chosen pieces fit together.
---

# choose

A page of alternatives the operator picks from, comments on and copies back into the chat in one pass. It replaces a long back-and-forth of questions: every decision is on one screen, each option shows what it would really look like, and the answer comes back as text the next turn reads.

`<SKILL_DIR>` is the base directory shown when this skill was loaded. The page is built by `<SKILL_DIR>/build.py` from a spec you write.

**Language.** These instructions are English. The page (titles, descriptions, sources, notes) is written in the language the operator is talking in, and `lang` in the spec sets its fixed labels (`pt-BR` or `en`): it is what they read and what their notes come back in.

## When not to

- One yes/no or two options without anything to look at: ask in the chat, or with the question tool.
- Nothing visual and nothing to compare side by side: a numbered list in the chat is enough.

## 1. Know what is being decided

Read the code and the product before listing options; an option that ignores how the thing works today is noise.

Turn the decision into **groups**, each one question:

- `one`: the options exclude each other (the layout, where a bar sits, which wording). Put the current state first when there is one, titled as such ("como está hoje"), and mark it `chosen`, so that leaving the group alone means keeping it.
- `many`: the options combine (features, columns, filters). Nothing is `chosen`.

Three to six options a group, at most ten groups a page. More than that is two rounds.

Keys are a letter for the group and a number for the option (`A1`, `B3`): short to read back, and the copied text names them.

## 2. Offer only what can be built

Before an option goes on the page, know where its data would come from and what it would take. Check the disk, the APIs and the tools' help text; a subagent can do the sweep. Put the answer in the option's `source`, and the size in its `tag` (`esforço pequeno`, `médio`, `grande`) with a `tone` (`good`, `warn`, `bad`).

When a picture shows a figure the product does not have yet, say in `source` that it is illustrative. An option that cannot be built is not offered; one that can only be built a worse way says which.

## 3. A real picture of each option

The operator chooses from what they see, so each picture is the thing itself:

- **Screens**: rendered by the project's own code, with its demo data, in a throwaway branch or worktree, never in the work under review. Follow the project's screenshot rules; in the deck, `.claude/rules/prints.md` forbids drawing a screen, so a prototype is a case in its picture tests, not a mockup.
- **Running app**: a screenshot of it.
- **Code, config, API shape, text**: a `code` block.
- **A change to something that exists**: the picture of today as `before` and the changed one as `image`. The card shows them side by side, and in the enlarged view the arrow keys flip one into the other in place, which is where a small change shows.

Same size, same data and same state across a group's pictures, so that the only difference is the option. Open every image before it goes on the page and check it shows what the option says.

## 4. Build the page

Write the spec as JSON in a temporary folder, beside its images:

```json
{
  "lang": "pt-BR",
  "title": "deck · aba agents · rodada 2: como fica na tela",
  "intro": "Todas as telas já trazem o que você escolheu na rodada 1.",
  "heading": "Escolhas da rodada 2 para a aba agents do deck:",
  "store": "deck-agents-rodada-2",
  "groups": [
    {
      "id": "L",
      "title": "A tela inteira, na versão mínima",
      "kind": "one",
      "help": "Escolha uma. Num terminal de 140 x 36.",
      "options": [
        {
          "key": "L1",
          "title": "Cartões em cima, a lista por conta e repositório",
          "what": "Os cartões das contas numa faixa no topo, e cada conta com os repositórios dela embaixo.",
          "source": "Tudo o que a rodada 1 escolheu.",
          "tag": "esforço médio",
          "tone": "warn",
          "image": "l1.svg",
          "chosen": true
        }
      ]
    }
  ]
}
```

| Field | Where | What |
|---|---|---|
| `lang` | page | `pt-BR` (default) or `en`: the page's fixed labels |
| `title`, `intro` | page | the heading, and a line on what is being chosen |
| `heading` | page | the first line of the copied text; the title when absent |
| `store` | page | where the browser keeps the choices; one per page, so two rounds never mix |
| `id`, `title`, `kind`, `help` | group | `kind` is `one` or `many`; `help` replaces "Escolha uma." / "Marque quantas quiser." |
| `key`, `title` | option | required |
| `what`, `source`, `tag`, `tone`, `alt` | option | what it does, where its data comes from, its size, the image's description |
| `image` | option | `.svg`, `.png`, `.jpg`, `.gif` or `.webp`, relative to the spec, inlined into the page |
| `before` | option | an image of today beside `image`, labeled before and after; needs `image` |
| `code` | option | a monospace block, escaped |
| `chosen` | option | checked when the page opens |

```bash
python3 -I <SKILL_DIR>/build.py <spec.json> <out.html>
```

It refuses a spec with a repeated id, a missing image or two `chosen` in a `one` group, and says which. Write the page where the operator can open it again, `~/Documents/<topic>-<round>.html`, never in a folder that gets cleaned with the session.

The page has, for every option, the picture (a click enlarges it) and a note; a free note at the end; a live preview of the text the button copies; the copy button at the end and on a bar that stays on screen; and the choices kept in the browser, so closing the tab loses nothing.

## 5. Check it, then open it

Before handing it over, read what the page copies as it opens:

```bash
google-chrome --headless --disable-gpu --user-data-dir=<temporary folder> --virtual-time-budget=3000 \
  --dump-dom file://<out.html> | grep -o '<pre id="preview">[^<]*'
```

and take a headless screenshot of its top to see that the pictures load. Then open it in the operator's own browser, detached:

```bash
nohup google-chrome <out.html> >/dev/null 2>&1 &
```

Never `xdg-open`: on the operator's machine it opens HTML in Slack.

Tell the operator, in a few lines, the groups and what is decided in each, what is illustrative, and that the button copies the choices to paste in the chat. Then wait.

## 6. Read the answer

What comes back:

```
Escolhas da rodada 2 para a aba agents do deck:

L. A tela inteira, na versão mínima: L1 Cartões em cima, a lista por conta e repositório
N. Nova sessão (n): N1 Barra embaixo, como o claude agents
   nota N1: Poderia ser um pouco mais clean
K. Mostrar ou esconder o modelo e os tokens: nenhuma
   nota K2 (não marcada): poder ordenar também

Mais: ...
```

A note weighs more than the title it sits on: it is the operator correcting the option. A note on an option not chosen is a request about that option, not a choice of it. `nenhuma` in a `many` group is a "no" to all of them; in a `one` group, a question you still have to ask. What comes after `Mais` is new input, sometimes a new requirement.

## 7. The next round, or the build

When the choices are pieces (features, columns, filters), the next round shows how they fit on one screen: whole screens that combine what was chosen, with the alternatives now about each piece's place and form. Carry every note as a constraint, drop what was not chosen, start the keys again with new letters, and give the page a new `store`.

Stop the rounds when every group has a choice and the notes ask for no new alternative. Then build it, and say that you took the last round as final.

## Never

- Never draw a screen where the project wants a real one, nor pass a mockup off as the product.
- Never offer an option you checked cannot be built.
- Never pre-choose for the operator beyond the current state of a `one` group.
- Never put real customer data, a token or a secret in a picture: demo data only. The page stays on the operator's machine; never upload or send it.
