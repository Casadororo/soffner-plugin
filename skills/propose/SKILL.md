---
name: propose
description: Use when the operator asks for a researched proposal of how to build something in their product (research how other tools do X and propose it for Y, faz um research de como, cria uma proposta em html), or invokes `/propose <topic> -- <context>`. Researches on the web how the products known for the topic solve it, studies the product and the code it would land in, and writes one self-contained HTML proposal, artifact-style and local, with the recommendation, the options weighed against this code, the design and a phased plan, then opens it in the browser. On the operator's pick (vamos de C), closes the open questions that are theirs and, when they name an aboard board, breaks the chosen option into a subboard of dependent cards. Never writes product code.
---

# propose

```
/propose <topic> -- <context>
```

| Argument | Read as |
|---|---|
| `topic` | what to research, in the operator's words (`real-time co-editing, like Google Sheets and Docs`). |
| `context` | where it would land and what makes it hard here (`the BI dashboards; Assis not only adds indicators, it can reorganize the whole panel`). Handed verbatim to both subagents. The hard part it names is the center of the proposal, not a footnote. |

No `--`: the whole text is the topic, and the context is the current repository plus the conversation. Ask only when neither names a product area.

The invocation authorizes web searches, reading the repository and writing one file under `~/Documents/propose/`. Writing to aboard is authorized only by an answer in [step 5](#5-the-answer) that names a board. Nothing else: no product code, no branch, no commit, nothing posted anywhere.

## 1. Research and study, in parallel

Two subagents in one message, so the sources and the code dumps stay out of this context. Each prompt carries the topic and the context verbatim, plus its brief:

**Research** (`general-purpose`, with WebSearch and WebFetch). How the products known for the topic solve it: the technique, what the user sees, what they gave up for it, and what it took them to get there. Engineering blogs, papers, official docs and conference talks over listicles. Also the open-source libraries that do it today, with their maturity (last release, who runs them in production). Returns one entry per approach: who uses it, how it works in a few lines, trade-offs, and a URL for every claim.

**Scenario** (`Explore`, very thorough). The product and the code the context names: what the feature does today and for whom (from `CLAUDE.md`, the project's docs, and the knowledge base when the session has one); its models, persistence, endpoints and front-end; the infrastructure already in place the topic would reuse (websockets, background jobs, cache, pub/sub, versioning, audit trail); and the hard part of the context traced in the code (in the example: through which entry point Assis changes a dashboard, and whether it is the same path as a human edit). Returns a map with `file:line` for every claim: what exists, what is missing, and the constraints (stack versions, deploy topology, tenancy).

## 2. Decide

Cross the two returns here, before writing a line of HTML:

- **2 or 3 options that fit this code**, not the catalog of the market. Each one names what it reuses from the code and what it adds.
- **The hard part of the context gets its own answer in every option.** An option that only works without it is not an option.
- **One recommendation**, the smallest step that delivers the value, with the step after it named.
- A claim about this code without `file:line`, or about another product without a URL, does not go on the page.

## 3. Write the page

`~/Documents/propose/<slug>.html`, with `-2`, `-3` when the name is taken. One self-contained file: inline CSS and JS, diagrams as inline SVG, no CDN and no web font, so it opens offline and travels as an attachment. It reads like an artifact: one column around 860px, a sticky table of contents, light and dark through `prefers-color-scheme`, options as cards, code identifiers in monospace.

The page is pt-BR, headings included: it is a proposal the operator takes to the pt-BR team (the plugin's "content published elsewhere" exception; do not translate it).

Sections, in this order:

1. **Resumo**: the recommendation in a few lines, and the one decision the reader has to make.
2. **Como os outros fazem**: a card per approach, with who uses it, how it works, the trade-offs and the links.
3. **Onde estamos hoje**: the product and the code as they are, with `file:line`, what already helps and what is missing.
4. **O desafio**: the hard part of the context, and why the market's answers do not cover it alone.
5. **Opções**: a table comparing them (effort, risk, what the user gets, what it reuses), then each one with its diagram.
6. **Proposta**: the recommended design, with an architecture diagram, one change followed end to end (from the click, or from Assis, to every other open screen), the data model changes and the main pieces to build.
7. **Plano**: phases, each shippable on its own, with a rough size.
8. **Riscos e perguntas em aberto**
9. **Fontes**

## 4. Check it, then open it

Screenshot it headless and look at the picture: the diagrams render, nothing overflows, dark mode is not a white page.

```bash
D=$(mktemp -d); google-chrome --headless --disable-gpu --user-data-dir=$D --window-size=1280,2400 \
  --screenshot=$D/page.png file://<page>; echo $D/page.png
```

Then open it in the operator's own browser, detached:

```bash
nohup google-chrome <page> >/dev/null 2>&1 &
```

Never `xdg-open`: on the operator's machine it opens HTML in Slack.

Report, in English: the path, the recommendation in one line, and the open questions the page leaves. Then wait for the answer.

## 5. The answer

The operator answers in their own words, for example `vamos de C, fecha as dúvidas que são pra mim e abre um subboard a partir de https://aboard.v360.io/boards/<slug>`. Only the pick is required; do the parts the answer asks for, in this order. When the conversation no longer holds the proposal, read the page back first.

### Close the operator's questions

Sort the open questions of the chosen option into two piles:

- **The operator's**: product, scope, priority, what the user sees, what is left out, who else has to agree. All of them are asked now, in one pass: AskUserQuestion, up to 4 per call, concrete options, the recommendation first. None is left "to define later".
- **The build's**: a library, a schema detail, a name, anything the code or a test settles. Decide each one here, with its reason. Never ask them.

Then update the page: the chosen option marked, **Plano** redone for it, and **Riscos e perguntas em aberto** becoming **Riscos e decisões**, with every answer and every decision. Check and reopen it as in step 4.

### Subboard, when the answer names a board

The board's slug is the last part of its URL. A subboard always hangs from a card, so:

1. **Read the parent.** `use_board(<slug>)` returns its usage text (the board's prompt) and its columns.
2. **The parent card.** The card the answer names, or a new one in the parent board (`create_card`, default column): first line the proposal in one sentence, then the chosen option, the decisions and the plan. The content goes in the card, not a path to the local page: nobody else can open it.
3. **The subboard.** `create_subboard(card_id, usage=<derived prompt>)`. Derive the prompt from the parent's: keep its text and every rule that still holds (base branch, skills, review and test criteria). Change only what this subboard narrows: its goal (the chosen option in a few lines), the decisions it is bound by, the order of its cards and what is out of scope. An agent that knows the parent's prompt should recognize this one.
4. **Columns stay as born.** The subboard comes with the parent's columns. Never `add_column`, `rename_column`, `move_column` or `delete_column`: no column per phase, no column per area.
5. **The cards**, in the subboard, all in the default column (todo), with no assignee.

**As few cards as possible.** A card is one PR that ships, is reviewed and is tested on its own. Never split by layer (backend, frontend, tests) when one PR carries all of it. Split only where an order is forced, where one PR would be too big to review, or where two parts can run in parallel.

**Each card stands alone.** The agent that picks it up never saw this conversation. First line the title, a verb and what changes. Then what to do, where in the code (the `file:line` from step 1), the decisions it applies, verifiable acceptance criteria and what is out of it.

**Dependencies with `blocked_by`.** It holds one card of the same board, and the board offers the card only once that one reaches review or done. Create the cards in dependency order, so the number exists when it is needed. A card that waits on two points to the one that lands last and names the other in its body. Cards that can run in parallel have no `blocked_by`.

The parent card, the subboard prompt and the cards are pt-BR: they are read by the pt-BR team and by the agents working its boards (the plugin's "content published elsewhere" exception; do not translate them).

Report, in English: the decisions closed, the subboard link, and the cards as `#id title ← #id` with what each waits on.
