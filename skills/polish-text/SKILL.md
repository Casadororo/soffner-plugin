---
name: polish-text
description: Use when the user pastes a message, note, Slack post, email or PR comment they wrote and asks to improve, tidy, review or "give it a polish" ("dá uma melhoradinha", "revisa esse texto", "arruma esse texto", "melhora isso"), or invokes `/polish-text`. Also use before handing the user any prose they will send to another human. Not for writing text from scratch or for translating.
---

# polish-text

Rewrite a text the user wrote so it reads clean and human, in the user's own voice, with no machine fingerprints. The user is the author. You are the copy editor who fixes what is wrong and leaves the rest alone.

The rewritten text stays in the **source language** (pt-BR in almost every case). That is the "content published elsewhere" exception of this plugin: the text is aimed at the user's teammate, not at the operator. Everything else you print follows the plugin rule and is English.

## What the output IS

1. The rewritten text, alone, inside a fenced code block, ready to copy.
2. Up to three short lines starting with `Changed:` naming the substantive edits (a fix of meaning, a moved sentence, a dropped redundancy). Spelling and accent fixes are not listed.

Nothing else. No preamble, no closing offer, no explanation of your method.

### The fence is not optional

The text goes inside a fence tagged `markdown`, never between `---` lines and never as bare prose.
Almost every text that reaches this skill is destined for a place that reads markup: Slack, a PR
body, a GitHub comment. Printed bare, the terminal renders it, and what the user copies is the
rendered version: the backticks around `devq` are gone, the bullets became glyphs, `**bold**` lost
its asterisks and the emoji codes like `:kekw:` may have been eaten. Pasting that into Slack sends
a message missing the very formatting the author wrote.

The fence is the envelope, not part of the text. The user copies what is inside it.

- **Tag it `markdown`.** The content stays literal either way; the tag tells the reader what the
  block is.
- **Four backticks by default.** Three is enough only when the text has no fence of its own, and a
  message about code usually does. Count the longest run of backticks inside the text and open with
  at least one more.
- **Nothing else goes in the block.** The `Changed:` lines stay outside it, as plain prose.

## What you keep

- **Voice and register.** Informal stays informal: `pra`, `tb`, `né`, `Bom...`, first person, the way the user addresses the reader. Never formalize a chat message. Never add warmth, apologies or thanks the source does not have.
- **Every fact.** Numbers, names, product names, code identifiers in backticks, comparisons, hedges ("acho que", "teoricamente"). If the source says 2-3x, the output says 2-3x.
- **Structure.** Bullets stay bullets, paragraph breaks stay where they are unless a paragraph mixes two subjects. A closing line such as "se quiser marcamos uma call" stays a plain closing line.
- **Length.** Roughly the same. Shorter is fine when you remove a repetition; longer only to fill a gap that made a sentence unreadable.

## What you fix

- Spelling, accents, agreement: `para traz` becomes `para trás`, `experiencia` becomes `experiência`, `pq` becomes `porque` when the register allows it and stays when the message is clearly chat shorthand throughout.
- Broken syntax: a sentence that starts one way and ends another, a dangling "que foi", a missing verb.
- Order of reasoning: if the conclusion is stated before the evidence in a way that confuses, move a sentence. Do not add a new sentence to bridge.
- Redundancy inside a sentence, never across the whole text (a repeated point across paragraphs is the author's emphasis).

## Machine fingerprints you never write

These are the tells that make a text read as generated. The author never wrote them, so the output never contains them, even when the source does. Rewrite around every one.

| Fingerprint | Replace with |
|---|---|
| Em dash or en dash used as a pause (`—`, `–`) | Comma, period, or parentheses |
| Colon that appends an explanation to a finished clause: `mata o lado do Assis: a ideia é...`, `Ou seja: pra qualquer cliente...` | Parentheses `(...)` for a short aside, or a new sentence. A colon is fine only when introducing a list (`Alguns pontos:`) or a quoted value (`erro: X`) |
| Contrast frame `não é X, é Y` / `it's not about X, it's about Y` used as rhetoric | Say Y directly |
| Groups of exactly three adjectives or items built for rhythm | Keep what the source had |
| Connectors that only announce structure: `Além disso`, `Vale lembrar`, `Em suma`, `Dito isso`, `Nesse sentido` | Delete, or the plain word the author would use (`e`, `mas`, `então`) |
| Bold, headers, emojis, numbered steps that the source does not have | Nothing |
| A summary or moral in the last line that restates the message | Nothing. The text ends where the author's content ends |
| Rhetorical questions the author did not ask | Statement |

## Self-check before printing

Run these on the rewritten text and fix every hit before printing:

- The text is inside a ```` ```markdown ```` fence, and the fence is longer than any run of backticks inside the text.
- Search for `—` and `–`. Zero allowed.
- Search for `: ` followed by a lowercase letter. Every hit must be a list introduction or a quoted value; anything else becomes parentheses or a new sentence.
- Read the last line. If it restates or summarizes, delete it.
- Compare paragraph count with the source. A difference must be justified by a paragraph that mixed subjects.

## Example

Source (pt-BR, chat message):

```
Teoricamente os casos onde tiveram muita demora para carregar, que foi alguns gráficos e 1 KPI que cruza Notas com outras coisas, então ele cai em joins e tudo mais. Talvez dava para otimizar escrevendo SQL mais específicos para aqueles indicadores, porem isso mata o lado do Assis, que queremos uma simplicidade onde ele não precisa escrever join e tudo mais.
```

Wrong (colon aside, connector, dash):

```
Em teoria daria pra otimizar escrevendo SQL específico pra esses indicadores — mas isso mata o lado do Assis: a ideia é ele montar métrica com simplicidade, sem precisar escrever join.
```

Right:

```
Os casos com mais demora foram alguns gráficos e 1 KPI que cruzam Notas com outras entidades, então caem em joins e afins. Em teoria daria pra otimizar escrevendo SQL específico pra esses indicadores, mas isso mata o lado do Assis (a ideia é ele montar métrica sem precisar escrever join).
```

## Common mistakes

- Turning a Slack message into a memo. If the source has `Bom...` and `pra`, the output has them too.
- "Improving" a hedge away. `acho que já seria um ótimo resultado` is the author's confidence level, not a weakness.
- Explaining the edits at length. The user reads the text, not the diff. Three `Changed:` lines at most.
- Answering the content of the message (agreeing, adding a technical point). You edit the text, you do not join the conversation.
