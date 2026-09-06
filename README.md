# radar-cvm

Agente que responde perguntas sobre documentos entregues à CVM por companhias
abertas brasileiras — fatos relevantes, comunicados ao mercado e avisos aos
acionistas — **citando empresa, categoria, data e página** em cada afirmação.

O problema que ele resolve não é "conversar sobre a bolsa". É este: um analista
precisa saber o que uma companhia comunicou, e uma resposta plausível porém
inventada é pior que nenhuma resposta, porque custa o mesmo tempo de conferência
e destrói a confiança no resto.

## O desenho, em uma frase

O modelo não recebe os documentos no prompt e não tem acesso ao corpus a não ser
por duas ferramentas. Se a busca não devolve nada, não existe caminho pelo qual
ele possa responder — a resposta correta passa a ser "não encontrei, e procurei
por isto".

Alucinação, aqui, não é algo que se pede ao modelo para evitar. É algo que a
arquitetura torna difícil.

```
índice IPE (CSV)  →  PDFs do RAD  →  texto por página  →  trechos  →  BM25
                                                                       ↓
                                              ferramentas ←  agente (Claude)
```

## Decisões, e por quê

**BM25 em vez de embeddings.** O vocabulário do domínio é fechado e literal:
"grupamento", "juros sobre capital próprio", "data-base", nomes de companhia. A
pergunta usa as mesmas palavras que o documento. Embeddings custariam uma chamada
de API por trecho na ingestão e uma dependência de modelo, para comprar
sinonímia num domínio que quase não tem sinônimos. A troca é reversível:
`Indice.buscar` é a única costura que o agente enxerga.

**A página é parte do trecho, não um enfeite.** Sem número de página a citação
não é verificável, e uma citação não verificável é indistinguível de uma
alegação. Por isso o número atravessa toda a pipeline, da extração ao prompt.

**Sobreposição entre trechos.** Um fato relevante costuma enunciar o valor numa
frase e a condição na seguinte. Cortar entre as duas produz um trecho que
responde errado sem parecer errado — o pior tipo de erro num sistema cuja
proposta é confiabilidade.

**Acento é removido na indexação.** A extração de texto de PDFs da CVM perde
diacríticos de forma inconsistente. Normalizar os dois lados faz "ações" da
pergunta casar com "acoes" do documento.

**A ingestão não derruba por um PDF ruim.** O corpus tem entregas malformadas e
páginas digitalizadas sem texto. São a exceção esperada, não um bug: o documento
é pulado, contado e reportado no fim.

## Uma armadilha do portal da CVM

O RAD — o sistema que serve os PDFs — **fecha a conexão sem responder quando o
User-Agent não é de navegador**. Não devolve 403; devolve "connection reset". E
às vezes responde 200 com uma página HTML de erro, que gravada como `.pdf` só
quebra muito depois, na extração, longe da causa. Por isso `documentos.baixar`
confere o cabeçalho `%PDF-` antes de gravar e falha alto.

## Uso

```bash
pip install -e ".[dev]"

# Monta o índice. Sem --limite, são milhares de documentos.
radar construir --ano 2026 --empresa "BANCO DO BRASIL" --limite 20

# Busca pura, sem LLM — confere o índice antes de gastar token.
radar buscar "grupamento de ações"

# Pergunta ao agente (requer credencial da Anthropic).
radar perguntar "O Banco do Brasil comunicou alguma mudança na política de dividendos?"
```

Ou por Docker:

```bash
docker build -t radar-cvm .
docker run --rm -v "$PWD/data:/app/data" radar-cvm buscar "recompra de ações"
```

## Provedor do modelo

O agente foi escrito contra o SDK da Anthropic, mas não está preso a ele. A
Z.ai serve os modelos GLM num endpoint que fala o mesmo protocolo, então trocar
de provedor é trocar URL base, chave e nome do modelo — o laço de ferramentas
não muda uma linha.

| Provedor | Modelo | Variável | Custo |
|---|---|---|---|
| `zai` (padrão) | `glm-4.7-flash` | `ZAI_API_KEY` | gratuito |
| `anthropic` | `claude-opus-5` | `ANTHROPIC_API_KEY` | pago |

```bash
export ZAI_API_KEY="..."          # padrão, não custa nada
RADAR_PROVEDOR=anthropic radar perguntar "..."   # para comparar
```

O padrão é o gratuito de propósito: rodar este projeto não deve custar dinheiro
a quem clonou para dar uma olhada. E manter os dois lado a lado transforma
"modelo pequeno dá conta?" num experimento de uma variável de ambiente, em vez
de uma reescrita.

Os subcomandos `construir` e `buscar` não precisam de credencial nenhuma — só
`perguntar`.

## Testes

```bash
pytest -q
```

A suíte não toca a rede nem o diretório `data/`. O corpus é reproduzível por
`radar construir`, e um teste dependente dele quebraria sempre que a CVM
estivesse fora do ar — o que não diria nada sobre o código.

## Fonte dos dados

Portal de dados abertos da CVM, conjunto IPE (Informações Periódicas e
Eventuais): <https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/>.
Um ZIP por ano com o índice de todas as entregas; em 2026 são 33.658
documentos, dos quais 7.138 nas categorias que este projeto indexa.

## O comportamento, observado

Rodado contra 8 documentos do Banco do Brasil, com `glm-4.7-flash`:

**Perguntado sobre JCP** — respondeu com R$ 5,2 bi distribuídos em 2025 (R$ 0,91
por ação) e R$ 866 mi no 1T26 (R$ 0,15 por ação), citando p.3 do comunicado de
09/03/2026 e p.2 do de 08/06/2026. Os quatro números foram conferidos contra as
páginas citadas: batem. A p.44 que ele também citou é a versão em inglês da
mesma página.

**Perguntado sobre a Petrobras**, que não está no índice — recusou, listou os
termos que tinha buscado, e percebeu sozinho que todos os resultados eram do
Banco do Brasil. Nenhuma tentativa de responder de memória.

Duas observações não são uma medição, e é por isso que a avaliação automatizada
é o próximo item.

## O que ainda não está aqui

- **Sem OCR.** Páginas digitalizadas sem camada de texto são descartadas em
  silêncio. Elas existem no corpus e hoje são um buraco não medido — não sei
  dizer quantas são.
- **Sem avaliação automatizada.** A regra de citação é verificada por leitura,
  não por um conjunto de perguntas com resposta esperada. É o próximo passo:
  sem medir taxa de citação e taxa de recusa correta, "não alucina" é uma
  afirmação sobre o desenho, não sobre o comportamento.
