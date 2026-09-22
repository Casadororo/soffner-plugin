# decide

Um passo que é só **escolha entre rótulos conhecidos** não precisa de um turno de modelo. `decide`
manda esse passo para um modelo de decisão local, que responde numa passada só, sem gerar texto, com
probabilidade calibrada.

Não é ferramenta de raciocínio. Ele escolhe de uma lista que você dá. Não lê três arquivos nem
infere que uma query quebra sob um tenant específico. Esse trabalho continua onde está.

## O contrato é o produto

O chamador ramifica pelo **exit code** e nunca precisa perguntar se a ferramenta está instalada.

| Exit | Significa | O chamador faz |
|------|-----------|----------------|
| `0` | Decidiu, no piso ou acima | Usa a resposta |
| `2` | Pedido errado: JSON inválido, tipo desconhecido, opções demais, prompt acima do orçamento | Conserta o pedido. Não é caminho de fallback, é bug de quem chamou |
| `3` | O binário existe, mas não há nada escutando | **Segue o caminho que já existia antes da ferramenta.** Não falha, não pede instalação |
| `4` | Respondeu abaixo do `--floor` | Escala: decide como decidiria sem a ferramenta |
| `127` | O binário não está no `PATH` | Igual ao `3`. **É o caso mais comum**, porque é o de quem nunca instalou nada |

O `127` não vem daqui: é o shell dizendo "command not found". Ele está na tabela porque é exatamente
o que uma máquina sem o plugin devolve, e quem só tratasse `3` ficaria sem ramo para esse caso.
Trate `127` e `3` como o mesmo caminho.

`3` e `4` são diferentes de propósito. `3` é "a ferramenta não está aqui". `4` é "a ferramenta está
aqui e diz que não sabe". Quem junta os dois perde o segundo sinal, que é o mais útil.

## Instalação

```bash
claude plugin marketplace add Casadororo/soffner-plugin
claude plugin install decide@soffner-plugin
```

O CLI precisa estar no `PATH`. O plugin não mexe no seu `PATH` sozinho:

```bash
ln -s ~/.claude/plugins/marketplaces/soffner-plugin/plugins/decide/bin/decide ~/.local/bin/decide
decide --version
```

O modelo é uma biblioteca Python e vem à parte:

```bash
decide install        # cria ~/.decide/venv e instala o laya nele
decide up             # sobe o sidecar e espera ele responder de verdade
decide selftest       # uma decisão de fixture; recusa resposta que não veio do modelo
```

`decide install` precisa do módulo `venv`. No Debian e no Ubuntu ele vem separado
(`apt install python3-venv`), e o comando diz isso quando falta.

## Uso

```bash
echo '{
  "state": { "goal": "triar a string", "trecho": "t.announcement.title" },
  "questions": {
    "precisa_traducao": { "type": "noul", "instructions": "Isso é texto exibido ao usuário final?" }
  }
}' | decide ask
```

Três tipos de pergunta: `choice` (rótulo de uma lista, com `probabilities` sobre todos),
`score` (nível numa escala ordenada, devolvido como esperança contínua) e `noul` (P(verdadeiro)).

O `confidence` de cada resposta é **entropia de Shannon normalizada**, não a maior probabilidade.
Uma divisão 0,51/0,49 tem probabilidade máxima alta e confiança perto de zero, que é justamente o
número que serve de piso.

## Por que o sidecar fica residente

O modelo não traz servidor: é biblioteca Python. Esse plugin escreve o servidor.

Checkpoint frio custa segundos por requisição; quente, na CPU, custa algumas centenas de
milissegundos. Por isso `decide up` **bloqueia até o sidecar responder um ping de verdade**, em vez
de subir em background e deixar o custo de carga escondido dentro da sua primeira decisão real. E
por isso `decide ask` nunca sobe o sidecar sozinho: subida implícita dentro de um hook trava o hook
num download.

## Três tetos que decidem se isso funciona

O orçamento do encoder é pequeno e rígido, e estourar não dá erro no modelo: dá **resposta errada
com confiança alta**. O `decide` recusa com exit `2` antes disso.

- **Opções por pergunta**: teto de 12. O prompt da pergunta e *todas* as opções dividem um orçamento
  só (192 tokens no `english`, 256 nos outros). Com sessenta opções sobram ~4 tokens por rótulo, os
  rótulos viram identificadores ilegíveis, e o modelo escolhe entre eles com alta confiança.
- **Tamanho do rótulo**: 48 caracteres. Rótulo é o que o modelo lê; frase não é rótulo.
- **Tamanho do estado**: 2400 caracteres, cortando pelo fim.

E uma regra de ordem: o `state` como objeto é renderizado em linhas `CHAVE: valor` **na ordem em que
você escreveu**, com o objetivo primeiro. Serializador que ordena chaves alfabeticamente empurra uma
lista longa para a frente do objetivo, e o modelo responde com confiança sobre uma pergunta que
nunca chegou nele.

## Honestidade sobre a confiança

A calibração publicada dentro das tarefas em que o modelo foi afinado é boa (ECE ~0,03). A
**zero-shot** não é (ECE ~0,20): fora dali ele erra com confiança alta o bastante para que um limiar
escolhido no olho seja chute com cara de número.

Então: tire o piso de uma amostra rotulada sua (30 a 50 casos que você já sabe a resposta),
verifique deterministicamente o que der para verificar depois da decisão, e trate o exit `4` como
tráfego normal. Ferramenta que abstém no caso difícil e acerta no fácil vale mais que ferramenta que
responde sempre.

## Quando não usar

- A resposta é prosa, diff, explicação ou plano.
- Os rótulos não são conhecidos antes de olhar. Ele escolhe de uma lista, não inventa a lista.
- A pergunta precisa de mais que algumas centenas de tokens para ser enunciada.
- Uma checagem determinística já responde. Um `grep` que acerta sempre ganha de um modelo que acerta
  quase sempre.
- A decisão é rara. Uma chamada por sessão não paga um processo residente; o ganho vem do volume.

## Modelo

[laya](https://github.com/NandhaKishorM/laya) (Convai Innovations), Apache-2.0, pesos abertos em
[huggingface.co/convaiinnovations](https://huggingface.co/convaiinnovations/laya). Três checkpoints:
`multilingual` (padrão aqui, mmBERT-base 322M), `english` (ModernBERT-large 421M) e
`typed-decisions` (ModernBERT-large 421M, afinado no split de treino do próprio benchmark que ele
pontua, então trate os números dele como in-domain).

O `--model` é sempre explícito. A biblioteca sabe rotear por idioma detectado, o que manda texto
não-inglês para o checkpoint multilingual independentemente da sua intenção, e trocar de checkpoint
entre requisições recarrega os pesos.
