"""Leitura do índice IPE da CVM — o catálogo de documentos entregues.

O índice é um CSV por ano; cada linha é um documento com metadados e um link
de download. Ele é a espinha do projeto: sem ele não há como saber quais PDFs
existem, nem atribuir empresa e data a um trecho de texto.
"""

from __future__ import annotations

import csv
import dataclasses
import io
import urllib.request
import zipfile
from collections.abc import Iterator
from pathlib import Path

from radar_cvm import fontes


@dataclasses.dataclass(frozen=True, slots=True)
class Documento:
    """Uma entrega de documento por uma companhia aberta.

    `protocolo` é a chave: identifica a entrega dentro do RAD e é estável
    entre execuções, então serve de nome de arquivo no cache.
    """

    protocolo: str
    empresa: str
    cnpj: str
    categoria: str
    assunto: str
    data_entrega: str
    url: str

    @property
    def id(self) -> str:
        return self.protocolo


def _linha_para_documento(linha: dict[str, str]) -> Documento | None:
    """Converte uma linha do CSV, ou devolve None se ela não for utilizável.

    Linhas sem link de download existem no índice (entregas canceladas, ou
    documentos que a companhia protocolou mas não publicou). Descartar aqui
    evita que o resto do sistema precise saber disso.
    """
    url = (linha.get("Link_Download") or "").strip()
    protocolo = (linha.get("Protocolo_Entrega") or "").strip()
    if not url or not protocolo:
        return None
    return Documento(
        protocolo=protocolo,
        empresa=(linha.get("Nome_Companhia") or "").strip(),
        cnpj=(linha.get("CNPJ_Companhia") or "").strip(),
        categoria=(linha.get("Categoria") or "").strip(),
        assunto=(linha.get("Assunto") or "").strip(),
        data_entrega=(linha.get("Data_Entrega") or "").strip()[:10],
        url=url,
    )


def ler_csv(texto: str) -> Iterator[Documento]:
    """Interpreta o conteúdo de um CSV do índice IPE já decodificado."""
    leitor = csv.DictReader(io.StringIO(texto), delimiter=fontes.SEPARADOR_CSV)
    for linha in leitor:
        documento = _linha_para_documento(linha)
        if documento is not None:
            yield documento


def baixar_indice(ano: int, destino: Path) -> Path:
    """Baixa o ZIP do índice de um ano e devolve o caminho do CSV extraído.

    Guarda o CSV em disco porque ele é reusado a cada filtro diferente, e
    baixar 1,6 MB da CVM a cada execução é desperdício e má vizinhança.
    """
    destino.mkdir(parents=True, exist_ok=True)
    csv_local = destino / f"ipe_{ano}.csv"
    if csv_local.exists():
        return csv_local

    url = fontes.URL_INDICE_IPE.format(ano=ano)
    with urllib.request.urlopen(url, timeout=120) as resposta:
        bruto = resposta.read()

    with zipfile.ZipFile(io.BytesIO(bruto)) as zip_indice:
        nomes = [n for n in zip_indice.namelist() if n.lower().endswith(".csv")]
        if not nomes:
            raise ValueError(f"ZIP do índice de {ano} não contém CSV: {zip_indice.namelist()}")
        conteudo = zip_indice.read(nomes[0])

    csv_local.write_bytes(conteudo)
    return csv_local


def carregar(
    csv_local: Path,
    *,
    categorias: tuple[str, ...] = fontes.CATEGORIAS_RELEVANTES,
    empresa: str | None = None,
) -> list[Documento]:
    """Lê o CSV do disco e aplica os filtros de categoria e empresa."""
    texto = csv_local.read_text(encoding=fontes.ENCODING_CSV)
    documentos = ler_csv(texto)
    if categorias:
        documentos = (d for d in documentos if d.categoria in categorias)
    if empresa:
        alvo = empresa.casefold()
        documentos = (d for d in documentos if alvo in d.empresa.casefold())
    return list(documentos)
