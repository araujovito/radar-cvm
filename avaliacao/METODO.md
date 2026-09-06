# Como este projeto se mede

Sem isto, "não alucina" é uma afirmação sobre o desenho. Com isto, é uma taxa.

## O que é medido

Vinte casos, divididos em dois tipos que testam falhas opostas:

- **12 respondíveis** — a resposta está no corpus. A falha aqui é *não achar*,
  ou achar e não citar.
- **8 ausentes** — a resposta não está no corpus. A falha aqui é *responder
  mesmo assim*, que é a falha que este projeto existe para impedir.

Um sistema que passa só nos respondíveis é um sistema que inventa. Um que passa
só nos ausentes é um que se recusa a trabalhar. As duas metades juntas é que
dizem alguma coisa.

## Corpus congelado

`corpus.json` fixa os oito protocolos, e o executor **reconstrói o índice a
partir deles** em vez de reaproveitar `data/indice.json`.

O motivo é específico: o índice IPE da CVM cresce ao longo do ano. Um recorte
por `--limite 8` selecionaria outros documentos daqui a um mês, e a avaliação
passaria a medir outra coisa sem avisar ninguém — o pior tipo de erro num
instrumento de medida, porque ele continua produzindo números.

## Correção sem juiz-modelo

Nenhum corretor chama LLM. Não é economia: um juiz-modelo traz a própria taxa
de erro para dentro do instrumento que deveria medir erro. Como o que interessa
aqui é objetivo — o número está no documento? há citação? recusou? — dá para
verificar direto.

| Métrica | O que checa | Exatidão |
|---|---|---|
| `taxa_citacao` | a resposta aponta ao menos uma página | exata |
| `taxa_fatos` | os valores esperados aparecem literalmente | exata |
| `taxa_recusa_correta` | admitiu não ter encontrado, **sem afirmar número** | exata |
| `taxa_ancoragem` | todo número da resposta existe no corpus | **aproximada** |

Duas decisões que valem explicação:

**Recusa com número não conta como recusa.** "Não encontrei o documento, mas o
lucro foi R$ 1,5 bilhão" é alucinação com verniz de humildade, e precisa contar
como falha.

**A ancoragem ignora inteiros curtos.** "30" e "99" aparecem por acaso em
qualquer documento; casá-los não prova nada, e mediria ruído nos dois sentidos.
Sobram os números específicos ("5,2", "0,91", "5.730.834"), onde a presença
significa alguma coisa. O preço: se o modelo reformata (`5.2` por `5,2`) ou soma
dois valores do documento, a métrica acusa sem ter havido invenção. É falso
positivo — acusa demais, não de menos —, que é o lado certo para um instrumento
errar quando o assunto é confiabilidade.

## Limites honestos desta avaliação

- **20 casos é pouco.** Um caso instável move a taxa em 5 pontos. Serve para
  detectar regressão grosseira, não diferença fina entre duas versões.
- **Uma repetição por caso.** O modelo é não determinístico; a mesma pergunta
  pode passar hoje e falhar amanhã. Sem repetição, não há como separar isso.
- **Um corpus só, de uma empresa só.** Os oito documentos são do Banco do
  Brasil. Nada aqui diz como o sistema se comporta com outra companhia, outro
  setor, ou um documento digitalizado.
- **Os casos foram escritos por quem construiu o sistema**, olhando o corpus.
  Isso enviesa para o que o sistema já faz bem. Casos vindos de perguntas reais
  de terceiros seriam mais duros.

## Rodar

```bash
radar avaliar --saida avaliacao/resultado.json
```

Com o provedor padrão (`glm-4.7-flash`, gratuito), custa zero.
