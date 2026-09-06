"""Roda a avaliação: monta o corpus congelado, pergunta, corrige, resume."""

from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path

from radar_cvm.agent.agente import responder
from radar_cvm.agent.provedor import Provedor, escolher
from radar_cvm.avaliacao import corretores
from radar_cvm.index.busca import Indice
from radar_cvm.index.trechos import dividir_documento
from radar_cvm.ingest import documentos as baixador
from radar_cvm.ingest import indice as catalogo
from radar_cvm.ingest import texto as extrator

PASTA = Path("avaliacao")


@dataclasses.dataclass(frozen=True, slots=True)
class Caso:
    id: str
    tipo: str  # "respondivel" | "ausente"
    pergunta: str
    fatos: list[str]


@dataclasses.dataclass(slots=True)
class Nota:
    caso: Caso
    resposta: str
    segundos: float
    acertou: bool
    citou: bool | None
    fatos_ok: bool | None
    recusou: bool | None
    ancorado: bool
    orfaos: list[str]
    erro: str | None = None


def carregar_casos(caminho: Path = PASTA / "casos.jsonl") -> list[Caso]:
    casos = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            casos.append(Caso(**json.loads(linha)))
    return casos


def montar_corpus(raiz: Path, config: Path = PASTA / "corpus.json") -> Indice:
    """Reconstrói o índice a partir dos protocolos congelados.

    Não reaproveita `data/indice.json`: aquele índice muda conforme o que foi
    ingerido por último, e uma avaliação cujo corpus muda em silêncio não
    mede nada de um mês para o outro.
    """
    dados = json.loads(config.read_text(encoding="utf-8"))
    alvos = set(dados["protocolos"])

    csv_local = catalogo.baixar_indice(dados["ano"], raiz)
    docs = [d for d in catalogo.carregar(csv_local, categorias=()) if d.protocolo in alvos]
    faltando = alvos - {d.protocolo for d in docs}
    if faltando:
        raise RuntimeError(f"Protocolos do corpus congelado sumiram do índice: {faltando}")

    trechos = []
    for doc in docs:
        pdf = baixador.baixar(doc, raiz / "cache")
        trechos.extend(dividir_documento(doc, extrator.extrair(pdf)))
    return Indice(trechos)


def corrigir(caso: Caso, resposta: str, corpus: str, segundos: float) -> Nota:
    passou_ancora, orfaos = corretores.ancorado(resposta, corpus)

    if caso.tipo == "ausente":
        # Um caso ausente só passa se o agente admitir que não achou. Se ele
        # responder qualquer coisa, é exatamente a falha que o projeto existe
        # para impedir.
        recusa = corretores.recusou(resposta)
        return Nota(
            caso=caso, resposta=resposta, segundos=segundos,
            acertou=recusa, citou=None, fatos_ok=None, recusou=recusa,
            ancorado=passou_ancora, orfaos=orfaos,
        )

    citacao = corretores.citou(resposta)
    fatos = corretores.trouxe_os_fatos(resposta, caso.fatos)
    return Nota(
        caso=caso, resposta=resposta, segundos=segundos,
        acertou=(citacao and fatos), citou=citacao, fatos_ok=fatos,
        recusou=None, ancorado=passou_ancora, orfaos=orfaos,
    )


def executar(
    indice: Indice,
    casos: list[Caso],
    *,
    provedor: Provedor | None = None,
) -> list[Nota]:
    provedor = provedor or escolher()
    cliente = provedor.cliente()
    corpus = " ".join(t.texto for t in indice.trechos)

    notas = []
    for caso in casos:
        inicio = time.monotonic()
        try:
            resposta = responder(caso.pergunta, indice, provedor=provedor, cliente=cliente)
            nota = corrigir(caso, resposta, corpus, time.monotonic() - inicio)
        except Exception as erro:  # noqa: BLE001
            # Falha de infraestrutura não é falha do modelo. Vira erro
            # declarado, não um zero que se confunde com resposta errada.
            nota = Nota(
                caso=caso, resposta="", segundos=time.monotonic() - inicio,
                acertou=False, citou=None, fatos_ok=None, recusou=None,
                ancorado=False, orfaos=[], erro=f"{type(erro).__name__}: {erro}",
            )
        notas.append(nota)
    return notas


def resumir(notas: list[Nota]) -> dict[str, object]:
    def taxa(selecao: list[Nota], campo: str) -> float | None:
        validos = [n for n in selecao if getattr(n, campo) is not None and n.erro is None]
        if not validos:
            return None
        return sum(bool(getattr(n, campo)) for n in validos) / len(validos)

    respondiveis = [n for n in notas if n.caso.tipo == "respondivel"]
    ausentes = [n for n in notas if n.caso.tipo == "ausente"]
    sem_erro = [n for n in notas if n.erro is None]

    return {
        "casos": len(notas),
        "erros": sum(1 for n in notas if n.erro),
        "acerto_geral": (sum(n.acertou for n in sem_erro) / len(sem_erro)) if sem_erro else None,
        "taxa_citacao": taxa(respondiveis, "citou"),
        "taxa_fatos": taxa(respondiveis, "fatos_ok"),
        "taxa_recusa_correta": taxa(ausentes, "recusou"),
        "taxa_ancoragem": taxa(sem_erro, "ancorado"),
        "segundos_por_caso": (
            sum(n.segundos for n in notas) / len(notas) if notas else None
        ),
    }
