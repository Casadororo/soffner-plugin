# soffner-plugin

Plugin pessoal de skills do [Claude Code](https://claude.com/claude-code). São os fluxos que eu
repito no dia a dia: passar trabalho para outra sessão, revisar o próprio diff antes de pedir
review, validar uma PR no browser e transformar uma PR em vídeo.

As skills não são genéricas de propósito. Cada uma carrega as decisões e as armadilhas que já
custaram uma sessão perdida, escritas como regra em vez de conselho. Elas assumem `git`, `gh` e um
projeto com `CLAUDE.md`, e leem do projeto as convenções que variam (branch de integração, comando
de teste, como subir o server).

## Skills

| Skill | O que faz |
|-------|-----------|
| `handoff` | Lado criador. Sobe um agente novo em background (`claude --bg`) com um brief escrito, espera o ACK de entendimento e libera com GO. |
| `handoff-accept` | Lado criado. Lê o brief, cria a worktree, valida premissas no código, devolve o ACK e só trabalha depois do GO. |
| `self-review` | Self-review competitivo do próprio diff: um revisor por arquivo de `.claude/rules/`, mais Banca e Juiz. Saída fixa: tabela única de achados, placar e gate para publicar como review na PR. |
| `dono` | Assume a propriedade de uma PR: resolve a PR, garante worktree com a branch dela, sincroniza com o remoto, carrega o contexto e executa a tarefa opcional dentro dessa worktree. |
| `polish-text` | Revisa um texto que você escreveu (Slack, e-mail, comentário de PR) mantendo sua voz, corrigindo ortografia e sintaxe e tirando cara de LLM. Saída: o texto pronto e até três linhas de mudanças. |
| `browser-test` | Valida uma PR já aberta no Chrome: lê a entrega, sobe (ou reaproveita) o server da worktree da PR, percorre cada comportamento entregue, tira print e devolve relatório com evidências. Gate de permissão em tudo que escreve fora do browser. |
| `browser-record` | Grava um mp4 de uma aba real do Chrome com o [aditor](https://github.com/victorlcampos/aditor), por CDP, num perfil que mantém os logins. Serve sozinha ou chamada por outra skill. |
| `demo` | Vídeo de demonstração de uma PR: planeja a rota, filma, monta com legenda e publica no corpo da PR numa seção `### Demo` com um texto curto do que aparece. |

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
| `handoff`, `handoff-accept`, `dono`, `self-review` | `git`, `gh` autenticado |
| `browser-test`, `demo` | extensão Claude in Chrome (ferramentas `mcp__claude-in-chrome__*`) |
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
