# soffner-plugin

Plugin pessoal de skills do [Claude Code](https://claude.com/claude-code). São os fluxos que eu
repito no dia a dia: assumir uma PR, atualizar a branch com a base, entregar a PR para revisão,
transformar uma PR em vídeo, anunciar a entrega no Slack, escolher entre alternativas numa página
só, polir um texto e deixar uma sessão autônoma melhorar um escopo do produto.

As skills não são genéricas de propósito. Cada uma carrega as decisões e as armadilhas que já
custaram uma sessão perdida, escritas como regra em vez de conselho. Elas assumem `git`, `gh` e um
projeto com `CLAUDE.md`, e leem do projeto as convenções que variam (branch de integração, comando
de teste, como subir o server).

## Skills

| Skill | O que faz |
|-------|-----------|
| `level-up` | Melhora um escopo (uma PR, uma parte do produto ou o produto inteiro) numa PR só, sem perguntar nada. Faz uma triagem curta que só lista melhoria com evidência (arquivo e linha, teste faltando, passo quebrado, TODO), dimensiona a rodada pelo tamanho da lista (lista vazia não gera PR; lista curta, uma etapa; lista longa, até três etapas, e o resto vira próximos passos na PR) e em cada etapa mexe direto no código, testa e commita. Sempre termina: não inventa trabalho, não faz rodada de avaliação e larga o item que passa do tamanho. |
| `dono` | Assume a propriedade de uma PR: resolve a PR, garante worktree com a branch dela (uma vaga do `bin/devslot` quando o repo tem o sistema e há vaga livre, senão uma worktree nova), sincroniza com o remoto, carrega o contexto e executa a tarefa opcional dentro dessa worktree. |
| `deliver` | Entrega a PR desta conversa para revisão: marca como ready for review, coloca a pessoa como revisora no GitHub e manda no Slack o pedido de review no seu formato (a frase pedindo, a lista com as PRs, mesmo que seja uma, e o contexto embaixo). Usa o que a conversa já sabe (qual PR, quem é a pessoa, o que a PR faz) e só busca o que falta. Nunca escolhe a PR numa lista. |
| `update-branch` | Traz a base para dentro da branch atual (merge, nunca rebase) e resolve os conflitos raciocinando pela intenção: base é a verdade, a mudança deliberada da PR é preservada. Lockfile, schema gerado, artefato de cron e arquivo de chaves têm regra própria. Faz o push no fim (nunca forçado), só com o merge fechado e nenhum teste vermelho. |
| `changelog` | O changelog periódico do deck e do vdev no #arquitetura-v360. Acha o último que você postou lá e junta tudo o que entrou depois dele, sem data para digitar: o do deck sai como anúncio, com o changelog PR a PR e os prints de `docs/` na thread, e o do vdev numa mensagem só, por seção (mudanças, entrou e saiu, no forno, quem mexeu). Salva o rascunho em `~/.cache/soffner-changelog/` e só posta depois do seu OK. |
| `announcement` | Anúncio de feature, melhoria ou Beta para o Slack: canvas longo com a mensagem de canal que aponta para ele, ou mensagem curta autocontida. Aceita uma PR como fonte e lê dela nome, motivação, setting e limitações; o que a PR não responde (disponibilidade, time, canal, demo) vai num gate só. Salva em `announcements/<slug>/` e imprime os blocos prontos para colar. Não posta nada. |
| `choose` | Uma página HTML para você escolher entre alternativas de uma vez: as opções em grupos (uma ou várias), cada uma com o print de verdade (ou antes e depois lado a lado, que as setas alternam na imagem ampliada) ou um trecho de código, de onde vem o dado e o esforço, uma nota por opção e uma no fim, e um botão que copia as escolhas para colar no chat. Confere o que copia antes de abrir no Chrome e trabalha em rodadas: a seguinte mostra como as peças escolhidas cabem juntas na tela. |
| `polish-text` | Revisa um texto que você escreveu (Slack, e-mail, comentário de PR) mantendo sua voz, corrigindo ortografia e sintaxe e tirando cara de LLM. Saída: o texto pronto e até três linhas de mudanças. |
| `demo` | Vídeo de demonstração de uma PR, sempre numa vaga do devslot que ocupa no início e solta no fim: planeja a rota, escreve cada cena como roteiro Playwright e ensaia sem câmera, filma tudo headless com cursor, capítulos e legendas desenhados na página, salva em `~/Videos` e publica no corpo da PR numa seção `### Demo` com um texto curto do que aparece. No fim apaga os arquivos de trabalho e derruba o servidor, sem perguntar. |

## Instalação

O repo é o próprio marketplace, então não tem clone manual nem submódulo:

```bash
claude plugin marketplace add Casadororo/soffner-plugin
claude plugin install soffner@soffner-plugin
```

O Claude Code clona sozinho dentro de `~/.claude/plugins/` e carrega o plugin na sessão seguinte.

As skills são invocadas com o prefixo do plugin:

```
/soffner:dono <pr>
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

Nenhuma skill instala nada no sistema; as que usam Playwright baixam o pacote para um cache do usuário. O que cada grupo espera encontrar:

| Skill | Precisa de |
|-------|-----------|
| `dono`, `update-branch` | `git`, `gh` autenticado |
| `deliver` | `gh` autenticado e o conector do Slack |
| `announcement` | `gh` autenticado, só quando a fonte é uma PR |
| `changelog` | `git`, `gh` autenticado, o conector do Slack, os clones do `deck` e do `v360-agents` em `~/Documents/Github/` e, para a imagem do anúncio do deck, `python3` com o Pillow |
| `choose` | `python3` e o Google Chrome |
| `level-up` | `git`, `gh` autenticado. Para olhar uma tela alterada, `node` e o Google Chrome (o recorder da `demo`). Dentro de uma vaga, a regra `devslot.md` do repo |
| `demo` | `gh` autenticado, `node`, `ffmpeg` no PATH e o Google Chrome instalado. Na primeira execução instala o Playwright fixado em `~/.cache/soffner-demo` (sem baixar navegador: usa o Chrome da máquina). Um repo com `bin/devslot` e uma vaga livre |

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
