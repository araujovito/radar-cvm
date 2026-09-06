"""Cache dos trechos já extraídos, para a ingestão poder ser retomada.

O PDF já tem cache, mas a extração não tinha: uma ingestão interrompida no
documento 3.000 refazia o trabalho de pypdf sobre os 2.999 anteriores. Com
7.138 documentos no corpus, isso transforma qualquer interrupção — Ctrl+C,
queda de rede, notebook fechado — em um recomeço.

Um arquivo por documento, e não um arquivo grande: gravar 7.138 vezes um JSON
que cresce é quadrático, e um único arquivo corrompido a meio caminho leva
tudo junto.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from radar_cvm.index.trechos import Trecho


def _caminho(protocolo: str, pasta: Path) -> Path:
    return pasta / f"{protocolo}.json"


def ler(protocolo: str, pasta: Path) -> list[Trecho] | None:
    """Devolve os trechos já extraídos, ou None se este documento é novo.

    Lista vazia é resposta legítima e diferente de None: significa "já
    processei e este documento não tem texto extraível" — sem isso, todo
    PDF digitalizado seria reprocessado a cada execução.
    """
    caminho = _caminho(protocolo, pasta)
    if not caminho.exists():
        return None
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Escrita interrompida no meio. Reprocessar é barato; confiar em JSON
        # truncado, não.
        caminho.unlink(missing_ok=True)
        return None
    return [Trecho(**d) for d in dados]


def gravar(protocolo: str, trechos: list[Trecho], pasta: Path) -> None:
    """Grava de forma atômica: ou o arquivo está inteiro, ou não existe."""
    pasta.mkdir(parents=True, exist_ok=True)
    destino = _caminho(protocolo, pasta)
    temporario = destino.with_suffix(".json.parcial")
    temporario.write_text(
        json.dumps([dataclasses.asdict(t) for t in trechos], ensure_ascii=False),
        encoding="utf-8",
    )
    temporario.replace(destino)
