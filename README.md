# soffner-plugin

Plugin pessoal de skills do [Claude Code](https://claude.com/claude-code). São os fluxos que eu
repito no dia a dia: abrir uma task sem errar a base, desenhar antes de codar, passar trabalho para
outra sessão, revisar o próprio diff antes de pedir review (a fundo ou numa passada rápida), triar o
review que chega, atualizar a branch com a base, validar uma PR no browser e transformar uma PR em
vídeo.

As skills não são genéricas de propósito. Cada uma carrega as decisões e as armadilhas que já
custaram uma sessão perdida, escritas como regra em vez de conselho. Elas assumem `git`, `gh` e um
projeto com `CLAUDE.md`, e leem do projeto as convenções que variam (branch de integração, comando
de teste, como subir o server).

## Skills

| Skill | O que faz |
|-------|-----------|
| `itask` | Confere o prompt de abertura de uma task antes de existir qualquer coisa em disco. Preenche worktree, branch base, branch nova (sempre em inglês, mesmo com o prompt em português) e próxima skill pelas convenções do projeto, mostra os quatro campos numa tabela com o goal e para até você confirmar. Sem skill de shape no repo, a próxima etapa é implementar direto. |
| `brainstorming` | Transforma uma ideia em design. Lê o repo para responder o que o repo responde, carrega o resto como suposição explícita e gasta sua atenção em lote, num gate só, em vez de uma pergunta por mensagem. Suposição rejeitada rebobina o trabalho até o último ponto aceito. |
| `handoff` | Lado criador. Sobe um agente novo em background (`claude --bg`) com um brief escrito, espera o ACK de entendimento e libera com GO. |
| `handoff-accept` | Lado criado. Lê o brief, cria a worktree, valida premissas no código, devolve o ACK e só trabalha depois do GO. |
| `self-review` | Self-review competitivo do próprio diff: um revisor por arquivo de `.claude/rules/`, mais Banca e Juiz. Saída fixa: tabela única de achados, placar e gate para publicar como review na PR. |
| `quick-review` | Passada rápida numa PR: uma onda só de lentes Sonnet em paralelo — bloat, teste que não se paga, buraco de produto, bug provável — e cada achado pesado por quanto o ajuste compra de verdade. Saída em `fix` / `call` / `cut`, mais uma linha dizendo se o código parece correto. Revisa e para: não edita nada, o conserto fica com a sessão que escreveu o código. Não lê `.claude/rules/`; profundidade é a `self-review`. |
| `full-review` | As quatro reviews de uma PR em ordem fixa: ponytail, `/super-review-gate` (avaliadores em Haiku), `/bug-hunter-gate` e ponytail de novo. Aplica os ajustes de cada review, roda os testes afetados e faz commit e push antes de começar a próxima. Pede sessão zerada e para se faltar algum dos gates no projeto. |
| `receiving-code-review` | Tria o review que chega (humano, thread inline ou o próprio `self-review`) pelo ganho real do ajuste: implementa o que compra alguma coisa, recusa com razão técnica o que não compra e manda para follow-up o que é válido mas fora do escopo da PR. |
| `dono` | Assume a propriedade de uma PR: resolve a PR, garante worktree com a branch dela, sincroniza com o remoto, carrega o contexto e executa a tarefa opcional dentro dessa worktree. |
| `update-branch` | Traz a base para dentro da branch atual (merge, nunca rebase) e resolve os conflitos raciocinando pela intenção: base é a verdade, a mudança deliberada da PR é preservada. Lockfile, schema gerado, artefato de cron e arquivo de chaves têm regra própria. Sem push. |
| `announcement` | Anúncio de feature, melhoria ou Beta para o Slack: canvas longo com a mensagem de canal que aponta para ele, ou mensagem curta autocontida. Aceita uma PR como fonte e lê dela nome, motivação, setting e limitações; o que a PR não responde (disponibilidade, time, canal, demo) vai num gate só. Salva em `announcements/<slug>/` e imprime os blocos prontos para colar. Não posta nada. |
| `polish-text` | Revisa um texto que você escreveu (Slack, e-mail, comentário de PR) mantendo sua voz, corrigindo ortografia e sintaxe e tirando cara de LLM. Saída: o texto pronto e até três linhas de mudanças. |
| `browser-test` | Valida uma PR já aberta no Chrome: lê a entrega, sobe (ou reaproveita) o server da worktree da PR, percorre cada comportamento entregue, tira print e devolve relatório com evidências. Gate de permissão em tudo que escreve fora do browser. |
| `browser-test-auto` | A `browser-test` sem ninguém no teclado: pega um lock da máquina (settings e Chrome são compartilhados), despacha um runner Opus novo em background que loga com um usuário temporário da PR, percorre a entrega sem perguntar nada e restaura as settings que mudou. A sessão que chamou audita cada print contra o que o runner afirmou antes de reportar. Só desktop. |
| `browser-record` | Grava um mp4 de uma aba real do Chrome com o [aditor](https://github.com/victorlcampos/aditor), por CDP, num perfil que mantém os logins. Serve sozinha ou chamada por outra skill. |
| `demo` | Vídeo de demonstração de uma PR: planeja a rota, filma, monta com legenda e publica no corpo da PR numa seção `### Demo` com um texto curto do que aparece. |

`brainstorming` e `receiving-code-review` nasceram no [superpowers](https://github.com/obra/superpowers)
do Jesse Vincent (MIT), portadas da versão 6.3.0 e reescritas para o plugin dele poder ficar
desligado. As duas diferenças são de propósito:

- **`brainstorming` gasta token para gastar menos atenção sua.** O original pergunta uma coisa por
  mensagem e pede aprovação a cada seção. Este lê o repo primeiro, anota o que sobrou como
  suposição explícita numa tabela e junta até quatro delas num gate só. O critério para parar
  deixou de ser o tamanho do passo e passou a ser o custo de errar: se refazer sai mais barato que
  perguntar, ele não pergunta. Cada suposição registra em que outras se apoia, então uma rejeição
  descarta tudo que dependia dela e volta ao último ponto aceito, em vez de deixar fóssil no design.
- **`receiving-code-review` não implementa por implementar.** O original verifica antes de aplicar;
  este exige que o ajuste compre alguma coisa. Bug, segurança e quebra passam direto. O resto
  responde quatro perguntas — o que quebra se não fizer, o ganho é observável, quanto custa, é
  escopo desta PR — e vira `implement`, `decline`, `follow-up` ou `blocked` numa tabela que sai
  antes da primeira edição. Estar certo não é o mesmo que valer a pena.

Também é de propósito que a `brainstorming` daqui **não** dispara sozinha: ela só entra com
`/soffner:brainstorming`.

Fora o crédito acima, **nenhuma skill do plugin referencia o superpowers**. Com ele desligado,
`itask` e `handoff` resolvem a próxima etapa pela cascata de quatro passos descrita em cada uma —
skill citada no prompt, `brainstorming`, skill de shape do projeto, implementar direto — e `dono`
não aponta mais para uma skill de debug que não existe mais aqui.

## Instalação

O repo é o próprio marketplace, então não tem clone manual nem submódulo:

```bash
claude plugin marketplace add Casadororo/soffner-plugin
claude plugin install soffner@soffner-plugin
```

O Claude Code clona sozinho dentro de `~/.claude/plugins/` e carrega o plugin na sessão seguinte.

As skills são invocadas com o prefixo do plugin:

```
/soffner:handoff <goal>
```

## Atualização

```bash
claude plugin marketplace update soffner-plugin
claude plugin update soffner
```

O Claude Code também refaz esse fetch por conta própria de tempos em tempos, então na prática um
push na `main` chega às máquinas sem ninguém rodar nada. O comando acima serve para quando você
quer a versão nova agora. Em qualquer dos casos a sessão precisa reiniciar para aplicar.

## Desenvolvimento local

Instalado pelo marketplace, mexer numa skill exige commit e push. Para o ciclo curto, carregue por
symlink em vez de instalar:

```bash
git clone https://github.com/Casadororo/soffner-plugin.git
ln -s "$PWD/soffner-plugin" ~/.claude/skills/soffner
```

Assim o plugin carrega como `soffner@skills-dir` e o arquivo editado vale na sessão seguinte
(`/reload-plugins` para valer na sessão atual). **Não deixe os dois caminhos ativos na mesma
máquina**: as mesmas skills apareceriam duas vezes, uma por origem.

## Dependências externas

Nenhuma skill instala nada. O que cada grupo espera encontrar:

| Skill | Precisa de |
|-------|-----------|
| `itask`, `handoff`, `handoff-accept`, `dono`, `self-review`, `quick-review`, `receiving-code-review`, `update-branch`, `browser-test-auto` | `git`, `gh` autenticado |
| `brainstorming` | nada além do repo |
| `full-review` | `git`, `gh` autenticado, o plugin ponytail e, no projeto, as skills `/super-review-gate` e `/bug-hunter-gate` |
| `announcement` | `gh` autenticado, só quando a fonte é uma PR |
| `browser-test`, `browser-test-auto`, `demo` | extensão Claude in Chrome (ferramentas `mcp__claude-in-chrome__*`) |
| `browser-record`, `demo` | [`aditor`](https://github.com/victorlcampos/aditor) no PATH, e um Chrome com porta de debug aberta |

O Chrome com porta de debug é um requisito do próprio Chrome, não do plugin: da versão 136 em
diante ele recusa `--remote-debugging-port` quando o diretório de dados é o padrão, e um segundo
`google-chrome` no mesmo diretório apenas conversa com a instância que já está rodando. A skill
`browser-record` explica o arranjo que resolve isso, com uma cópia do perfil que preserva os
logins.

## Convenções

Skill é escrita em inglês, incluindo descrição, instruções e prompts de subagent. A exceção é o
conteúdo que a skill publica num destino pt-BR, como corpo de PR e review no GitHub. Regra
completa, com o porquê, em [CLAUDE.md](CLAUDE.md).

## Adicionar skill nova

```bash
mkdir -p skills/<nome>
$EDITOR skills/<nome>/SKILL.md
claude plugin validate .
```

Duas armadilhas de frontmatter que o `validate` pega e que passam batido no olho:

- `": "` no meio da `description` sem quotes quebra o YAML, e a skill carrega com metadata vazia,
  silenciosamente.
- `name` tem que casar com o nome do diretório.

## Licença

MIT. Ver [LICENSE](LICENSE).
