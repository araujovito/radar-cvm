"""Índice de busca BM25 sobre os trechos.

Por que BM25 e não embeddings: o vocabulário aqui é fechado e literal —
"grupamento", "JCP", "recompra", "data-base", nomes de companhia. A pergunta
que o usuário faz usa as mesmas palavras que o documento. Embeddings
custariam uma chamada de API por trecho na ingestão e uma dependência de
modelo, para ganhar sinônimo num domínio que quase não tem sinônimo.

A troca é consciente e reversível: `Indice.buscar` é a única costura que o
agente enxerga.
"""

from __future__ import annotations

import dataclasses
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from radar_cvm.index.trechos import Trecho

# Parâmetros clássicos do BM25. k1 controla a saturação da frequência do termo
# e b, quanto o tamanho do documento penaliza.
K1 = 1.5
B = 0.75

# Palavras que aparecem em quase todo documento da CVM e só diluem o ranking.
VAZIAS = frozenset(
    """a o e de da do das dos em no na nos nas um uma uns umas para por com sem
    que se ao aos as os como mais ou tambem sobre sua seu suas seus sao foi ser
    nao entre pelo pela nesta neste desta deste companhia s.a sa ltda""".split()
)


def normalizar(texto: str) -> list[str]:
    """Quebra em termos comparáveis: minúsculo, sem acento, sem palavra vazia.

    Remover acento é o que faz "acionistas" casar com "acionístas" e com o
    texto de PDFs cuja extração perde diacríticos — isso acontece no corpus.
    """
    sem_acento = unicodedata.normalize("NFKD", texto.casefold())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    termos = re.findall(r"[a-z0-9]+", sem_acento)
    return [t for t in termos if t not in VAZIAS and len(t) > 1]


@dataclasses.dataclass(frozen=True, slots=True)
class Resultado:
    trecho: Trecho
    escore: float


class Indice:
    """Índice BM25 em memória, persistível em JSON."""

    def __init__(self, trechos: list[Trecho]) -> None:
        self.trechos = trechos
        self._termos: list[Counter[str]] = [Counter(normalizar(t.texto)) for t in trechos]
        self._tamanhos = [sum(c.values()) for c in self._termos]
        self._media = (sum(self._tamanhos) / len(self._tamanhos)) if self._tamanhos else 0.0

        documentos_com: Counter[str] = Counter()
        for contagem in self._termos:
            documentos_com.update(contagem.keys())
        total = len(trechos)
        # IDF do BM25 com o +0.5 de suavização; o max(…, 1e-9) evita que um
        # termo presente em todos os trechos vire peso negativo.
        self._idf = {
            termo: max(math.log((total - n + 0.5) / (n + 0.5) + 1.0), 1e-9)
            for termo, n in documentos_com.items()
        }

    def __len__(self) -> int:
        return len(self.trechos)

    def buscar(self, pergunta: str, *, limite: int = 5) -> list[Resultado]:
        consulta = normalizar(pergunta)
        if not consulta or not self.trechos:
            return []

        escores = []
        for i, contagem in enumerate(self._termos):
            escore = 0.0
            for termo in consulta:
                frequencia = contagem.get(termo, 0)
                if not frequencia:
                    continue
                norma = 1 - B + B * (self._tamanhos[i] / self._media if self._media else 1)
                escore += self._idf[termo] * (frequencia * (K1 + 1)) / (frequencia + K1 * norma)
            if escore > 0:
                escores.append(Resultado(trecho=self.trechos[i], escore=escore))

        escores.sort(key=lambda r: r.escore, reverse=True)
        return escores[:limite]

    def por_protocolo(self, protocolo: str) -> list[Trecho]:
        """Todos os trechos de um documento, em ordem de página."""
        achados = [t for t in self.trechos if t.protocolo == protocolo]
        return sorted(achados, key=lambda t: t.pagina)

    def salvar(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        dados = [dataclasses.asdict(t) for t in self.trechos]
        caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def carregar(cls, caminho: Path) -> "Indice":
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return cls([Trecho(**d) for d in dados])
