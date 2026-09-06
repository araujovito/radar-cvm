"""Extração de texto dos PDFs, preservando o número da página.

A página é o que torna a citação verificável: sem ela o agente só pode dizer
"segundo o fato relevante da empresa X", e quem lê não tem como conferir.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path


@dataclasses.dataclass(frozen=True, slots=True)
class Pagina:
    numero: int  # 1-indexado, como o leitor de PDF mostra
    texto: str


def extrair(pdf: Path) -> list[Pagina]:
    """Devolve as páginas com texto de um PDF.

    Páginas sem texto extraível (digitalizações, páginas só com imagem) são
    descartadas em silêncio — elas existem no corpus da CVM e não há OCR aqui.
    Um documento inteiro sem texto vira lista vazia, e quem chama decide.
    """
    from pypdf import PdfReader  # import tardio: mantém a ingestão de índice sem dependências

    leitor = PdfReader(str(pdf))
    paginas = []
    for numero, pagina in enumerate(leitor.pages, start=1):
        conteudo = (pagina.extract_text() or "").strip()
        if conteudo:
            paginas.append(Pagina(numero=numero, texto=conteudo))
    return paginas
