"""Como uma resposta é julgada.

Nenhum corretor usa LLM. São verificações determinísticas, e isso é uma
escolha, não economia: um juiz-modelo introduz a própria taxa de erro no
instrumento que deveria medir erro. Como o que interessa aqui é objetivo —
o número está no documento? há citação? recusou? — dá para checar direto.

O preço dessa escolha está declarado em cada função: as duas primeiras são
exatas, a terceira é aproximada e pode acusar falso positivo.
"""

from __future__ import annotations

import re
import unicodedata

# "p. 3", "p.3", "página 12", "pagina 12" — as formas que o agente produz.
PADRAO_PAGINA = re.compile(r"\bp(?:\.|ágina|agina)\s*\d+", re.IGNORECASE)

# Números com vírgula decimal ou separador de milhar: 5,2 / 0,91 / 5.730.834.
# Inteiros de até 3 dígitos ficam de fora de propósito — ver `ancorado`.
PADRAO_NUMERO = re.compile(r"\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?|\d+,\d+")

# O agente não tem um formato fixo de recusa; estas são as marcas que
# distinguem "não encontrei" de uma resposta afirmativa.
MARCAS_RECUSA = (
    "nao encontrei",
    "nao ha",
    "nao consta",
    "nao foi encontrado",
    "nao localizei",
    "nenhum documento",
    "nenhum trecho",
    "nao esta disponivel",
    "nao aparece",
    "sem informacao",
    "nao ha documentos",
)


def _dobrar(texto: str) -> str:
    """Minúsculo e sem acento, para comparar texto de PDF com texto de modelo."""
    sem = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in sem if not unicodedata.combining(c))


def citou(resposta: str) -> bool:
    """A resposta aponta ao menos uma página?

    Exato: ou o padrão de página está lá, ou não está.
    """
    return bool(PADRAO_PAGINA.search(resposta))


def trouxe_os_fatos(resposta: str, fatos: list[str]) -> bool:
    """Todos os valores esperados aparecem na resposta?

    Exato, e por isso os fatos do caso são escritos como o documento os
    escreve ("5,2", não "5.2 bilhões"): o teste é presença literal.
    """
    return all(fato in resposta for fato in fatos)


def recusou(resposta: str) -> bool:
    """A resposta admite não ter encontrado?

    Exato quanto à marca, mas exige que a recusa não venha acompanhada de
    afirmação numérica — "não encontrei X, mas o valor é 1,5 bilhão" é uma
    alucinação com verniz de humildade, e precisa contar como falha.
    """
    dobrada = _dobrar(resposta)
    tem_marca = any(marca in dobrada for marca in MARCAS_RECUSA)
    return tem_marca and not PADRAO_NUMERO.search(resposta)


def ancorado(resposta: str, corpus: str) -> tuple[bool, list[str]]:
    """Todo número da resposta existe no corpus?

    Esta é a medida de alucinação, e é a única **aproximada** das quatro.

    Só olha números com vírgula decimal ou separador de milhar. Inteiros
    curtos ficam de fora porque "30" e "99" aparecem em qualquer documento
    por acaso, e casá-los não prova nada — o que os torna ruído nos dois
    sentidos. O que resta ("5,2", "0,91", "5.730.834") é específico o
    bastante para que a presença signifique alguma coisa.

    Onde ela erra: se o modelo reformata ("5.2" em vez de "5,2") ou soma
    dois valores do documento, o número não casa e o caso é acusado sem ter
    havido invenção. É falso positivo — acusa demais, não de menos —, que é
    o lado certo para um instrumento errar quando o assunto é confiabilidade.

    Devolve (passou, números não encontrados).
    """
    corpus_dobrado = _dobrar(corpus)
    orfaos = [
        numero
        for numero in PADRAO_NUMERO.findall(resposta)
        if numero not in corpus_dobrado
    ]
    return (not orfaos), orfaos
