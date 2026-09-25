---
name: announcement
description: Use when the user asks for a Slack announcement of a feature, improvement or beta (anúncio, anuncia essa feature, canvas de lançamento, mensagem pro canal), or invokes `/announcement`, optionally with a pull request as the source. Drafts a long canvas, a channel message pointing at it, or a standalone short message, in pt-BR, saved to a file and printed ready to copy. Never posts to Slack.
---

# announcement

Turn a feature, improvement or beta into a Slack announcement that someone from another area of the company understands, and that a technical reader can act on (test it, turn on the setting, give feedback) without asking for more.

**Language.** These instructions are English. The announcement is **pt-BR with correct accents** (`ç`, `ã`, `á`, `é`, `ê`, `ô`, `à`...), because it goes to the pt-BR team on Slack: the plugin's "content published elsewhere" exception. That is why every template and example below is pt-BR; do not translate them. Established English terms stay English (Beta, setting, role, feature flag). What you print to the operator around the blocks is English.

The skill drafts. It never posts to Slack, never creates a canvas through a Slack tool, and never sends anything.

## Arguments

| Invocation | Output |
|---|---|
| `/announcement` | ask for the source |
| `/announcement <description or PR>` | mode picked from the content, confirmed in the gate |
| `/announcement completo <...>` | canvas + channel message pointing at it |
| `/announcement curta <...>` | standalone short message |
| `/announcement canvas <...>` | canvas only |

The mode keywords stay pt-BR for the same reason skill names are exempt: they are what the operator types. A PR is a URL or a number (`#48718`, `48718`) resolved against the current repo.

## 1. Gather

Whatever the source, the announcement needs:

1. Feature name (short, pt-BR, becomes the title)
2. The problem or context it solves
3. How it works, 3-5 points
4. Beta/testing or production
5. Where it is available (TST, production, partial production)
6. Setting, feature flag or permission gating access
7. Demo, video or recording (canvas only)
8. Known limitations (Beta only)
9. Responsible team (Dados, Plataforma, Reports...) and the feedback channel

### From a PR

```bash
gh pr view <pr> --json number,title,body,state,mergedAt,baseRefName,files,url
gh pr diff <pr>
```

Read the PR before asking anything; it answers most of the list:

| Field | Where it is in the PR |
|---|---|
| Name | the title, reworded as a feature name for someone who does not code |
| Problem | the why section of the body (`Motivação`) |
| How it works | `Descrição` and `Resumo da Solução`, translated from files changed into what the user sees on screen |
| Setting, flag, permission, role | the diff (setting definitions, `default:` values, role names) and `Pontos de Atenção` |
| Who is affected | the customer impact section |
| Limitations | `Pontos de Atenção` |

A PR body is written for a reviewer and the announcement for someone who never opens the code. A file path or class name never reaches the announcement; a setting or role name does, in backticks, because the reader needs it to act.

Availability is a fact the PR only hints at. Open means not available anywhere yet; merged means it is on the base branch, not that it reached an environment. Never turn a base branch into an environment or a date. Ask.

### The gate

Everything still missing goes in **one `AskUserQuestion` call**, up to four questions, never one message per question. Skip every field the input or the PR already answered.

- Offer the likely answers as options (drafted from the PR when there is one); "Other" takes free text.
- The mode is a question only when no keyword was given. Suggest `completo` for a big improvement with several sections, a Beta or a demo; `curta` when one or two paragraphs cover it. The suggestion is the first option, marked `(Recommended)`.
- `curta` also asks whether to include `@aqui`.
- More than four open fields: a second call with the rest, never a third.
- A field that is pure free text with no plausible options (the problem, when there is no PR and the description is vague) goes in one plain message that lists all such fields at once.

Pick the slug yourself: short English snake_case (`report_builder_v1`, `bulk_edit_items`). It shows up in the delivery; renaming is cheap, so it is not worth a question.

## 2. Tone

- Halfway between plain and technical. No bare dev jargon without context, and no talking down.
- Never `--`, never an em or en dash. Rewrite with a comma, parentheses, a colon or a new sentence.
- No marketing words ("revolucionário", "game changer", "transformador").
- No "Estamos super animados", "felizes em anunciar", "com prazer apresentamos" or variants.
- No hedging ("talvez", "às vezes", "pode ser que").
- None of the machine fingerprints listed in `/soffner:polish-text`.
- Integrate what the operator says, never paste it raw. Rewrite it in the tone of the rest, put it in the right section, and update the sections that change with it (a new access scope touches both `Status atual` and `Settings e permissões`).
- Never invent a setting, permission, link or team name. From the PR diff is a source; from nowhere means ask.
- No lorem ipsum and no vague placeholder (`[descrição aqui]`). The only allowed placeholder is `Vídeo em breve` in the demo section.

### Emojis

Few: at most one per canvas section, 0-2 in a channel message. Always the Slack code (`:rocket:`), never the unicode character.

| Context | Emojis |
|---|---|
| General announcement | `:rocket:` `:sparkles:` `:tada:` (sparingly) |
| Beta, warning | `:warning:` `:test_tube:` `:construction:` |
| Data, reports | `:bar_chart:` `:chart_with_upwards_trend:` `:clipboard:` |
| Security | `:lock:` `:closed_lock_with_key:` |
| Configuration | `:gear:` `:wrench:` |
| Demo, video | `:joystick:` `:movie_camera:` `:tv:` |
| Feedback | `:raised_hands:` `:speech_balloon:` |

### Markup

A **canvas renders standard markdown**. A **channel message uses Slack mrkdwn**. Never mix them.

| | Canvas | Channel message |
|---|---|---|
| Bold | `**text**` | `*text*` |
| Italic | `*text*` | `_text_` |
| Strike | `~~text~~` | `~text~` |
| Heading | `#`, `##`, `###` | none; use `*bold line*` |
| List | `-` | `•` |
| Link | `[text](url)` | `<url\|text>` |
| Code block | ```` ``` ```` | ```` ``` ```` without a language |
| Inline code, quote | same in both | same in both |

## 3. Templates

Bracketed text is an instruction to you, never output.

### Canvas (`completo`, `canvas`)

```markdown
# [feature name]

[Opening line: who is announcing and what the improvement is.]

[optional emoji] **[feature name]**

[What it is, in one plain sentence. 2-3 lines at most.]

## :test_tube: Status atual

[Where it is available and who can use it.]

[Beta only:]
:warning: **Importante: mecanismo em Beta**

Isso significa que ainda está em fase de testes e pode apresentar limitações:

- [limitation]
- [limitation]
- A melhoria pode ser desativada a qualquer momento durante essa fase.

## :jigsaw: O que é [feature name]?

[What it is for and what it lets the user do, 1-2 paragraphs.]

[When there is a data source or scope:]
Atualmente [scope].

A partir dela é possível:

- [capability]
- [capability]

## :lock: Segurança e visibilidade

[How it handles permissions, usually by following the existing ones. Be explicit about what the user can and cannot see.]

## :outbox_tray: Como funciona [main action]

[The flow as the user lives it.]

[When there is a prerequisite:]
**Importante:** [prerequisite]

## :gear: Settings e permissões

**Setting do mecanismo**
[What it controls, current default.]

**Setting de permissionamento**
[What it controls, current default.]

**Permissão necessária:** [role or permission]

## :joystick: Demo

[Video, GIF or screenshot link, or "Vídeo em breve".]

## :speech_balloon: Feedback

Qualquer feedback, bug encontrado ou comportamento inesperado, avisem [team] no canal [#channel] ou em DM.
```

- One emoji at the start of each `##`, never more.
- A section that does not apply is dropped whole, never left empty.
- No fact appears in two sections.
- 60 lines at most.

### Channel message pointing at the canvas (`completo`)

```
[Greeting for the time of day, or "Pessoal,"], [team] está [iniciando os testes de / anunciando] [kind of change]:

*[feature name]*

[One line: where it is available and for whom.]

[Beta only:] Importante: o mecanismo ainda está em Beta, então podem existir limitações, funcionalidades faltantes ou mudanças durante essa fase de testes.

[One paragraph, 2-3 lines: what it lets people do, at a high level.]

Criei um canvas com mais detalhes sobre a funcionalidade e como ela funciona[, e um vídeo demo].

Qualquer feedback é super bem-vindo! :raised_hands:
```

- 10 lines at most, no long lists (those belong in the canvas).
- 0-1 emoji; the closing `:raised_hands:` is optional.
- The team is named once.
- Unknown time of day: `Pessoal,` or no greeting.

### Standalone short message (`curta`)

More detail than the message above, because there is no canvas behind it.

```
:rocket: [Novidade / Melhoria / Em breve]: [short feature name]

[1-2 lines: what it is, at the highest level.]

@aqui

*Como funciona (resumo):*
• [step]
• [step]
• [step]

[One line on availability: test environment, production, expected date.]

:bar_chart: Limite: [numeric limit]
:closed_lock_with_key: Permissão necessária: [permission]

:warning: [important warning]

Se encontrarem bugs ou comportamentos inesperados, por favor avisem o time de [team].

[PS: a non-obvious test prerequisite.]
```

- 1-3 emojis, each in front of a key fact (limit, permission, warning). A line whose fact does not exist is dropped.
- `@aqui` only when the gate said yes.
- PS only for a prerequisite nobody would guess.
- The example in section 5 is about the ceiling in length.

## 4. Deliver

Write the file at `<repo root>/announcements/<slug>/announcement.md` (the current directory when not in a repo). It is scratch: never stage or commit it. It holds only the copyable blocks, no title, metadata, checklist or notes:

````markdown
## Canvas

```
[canvas]
```

## Channel message

```
[channel message]
```
````

Fences carry no language, so `:emoji:` codes stay literal. `curta` has only the channel message section; `canvas` has only the canvas section.

Then, in the chat:

1. `Saved to [announcements/<slug>/announcement.md](announcements/<slug>/announcement.md)`.
2. The same blocks inline, so the operator copies without opening the file.
3. The checklist, run by you before printing. Print only the items still open for the operator, not the ones that pass:
   - feedback channel filled in
   - demo link filled in, or the placeholder is deliberate
   - settings and permissions confirmed
   - responsible team correct
   - no `--` or dash
   - emojis within the limits
4. `Anything to adjust?`

A revision rewrites the same file. Never a `-v2` copy.

## 5. Examples

Canvas, abbreviated:

```
# Construtor de Relatórios Customizados

O time de Dados está apresentando uma melhoria nova que começa a ser testada agora.

:bar_chart: **Construtor de Relatórios Customizados**

Permite criar relatórios customizados direto pela interface, escolhendo quais dados extrair.

## :test_tube: Status atual

Disponível nos ambientes TST para usuários V360 testarem.

:warning: **Importante: mecanismo em Beta**

Ainda está em fase de testes e pode apresentar limitações:

- Algumas funcionalidades podem não funcionar exatamente como esperado
- Existem funcionalidades que ainda serão adicionadas
- A performance ainda não foi testada extensivamente em clientes grandes
- A melhoria pode ser desativada a qualquer momento durante essa fase

## :jigsaw: O que é o Construtor de Relatórios?

[...]
```

Channel message pointing at that canvas:

```
Boa tarde, pessoal, o time de Dados está iniciando os testes de uma nova melhoria:

*Construtor de Relatórios Customizados*

A funcionalidade já está disponível em TST para usuários V360 testarem.

Importante: o mecanismo ainda está em Beta, então podem existir limitações, funcionalidades faltantes ou mudanças durante essa fase de testes.

De forma geral, ele permite montar relatórios personalizados a partir de Documentos Fiscais, escolhendo colunas, filtros, agregações e ordenações diretamente pela interface.

Criei um canvas com mais detalhes sobre a funcionalidade, como ela funciona e um vídeo demo.

Qualquer feedback é super bem-vindo! :raised_hands:
```

Standalone short message:

```
:rocket: Novidade em breve: edição de itens em massa via Excel

Agora será possível editar itens de documentos em massa diretamente pela listagem de processos, usando uma planilha Excel.
Isso permite alterar centenas ou até milhares de itens de uma vez, sem precisar editar documento por documento.

@aqui

*Como funciona (resumo):*
• Selecione os documentos na listagem do processo (checkbox ou filtro)
• Clique em "Editar itens em massa" no menu de ações e selecione as colunas chave
• O sistema gera uma planilha Excel em segundo plano
• Você recebe a planilha por e-mail
• Edite os campos necessários
• Faça o upload da planilha para aplicar as alterações

A melhoria já está disponível nos ambientes de teste e estará disponível em produção no início do mês que vem.

:bar_chart: Limite: até 10.000 itens por operação
:closed_lock_with_key: Permissão necessária: role `bulk_edit_items` no módulo vprocessmanager

:warning: Os campos editáveis respeitam as permissões de workflow de cada processo.

Se encontrarem bugs ou comportamentos inesperados, por favor avisem o time de plataforma.

PS: o envio da planilha acontece por e-mail. Para testar em TST, é necessário procurar o time de Infra e pedir para entrar no grupo que recebe os e-mails de TST.
```

## When NOT to use

- Polishing an announcement the user already wrote: `/soffner:polish-text`.
- Describing a PR for its reviewers: that is the PR body, not an announcement.
