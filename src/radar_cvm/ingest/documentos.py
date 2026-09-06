"""Download dos PDFs no RAD, com cache em disco.

O RAD é o sistema da CVM que serve os documentos em si. Ele é mais frágil que
o portal de dados abertos: exige User-Agent de navegador e não devolve erro
HTTP quando recusa — fecha a conexão.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

from radar_cvm import fontes
from radar_cvm.ingest.indice import Documento

# Um PDF de fato relevante tem tipicamente 100-400 KB. Nada perto de 20 MB é
# um documento normal, e baixar um anexo gigante trava a ingestão por um
# item só.
LIMITE_BYTES = 20 * 1024 * 1024


class DownloadRecusado(RuntimeError):
    """O RAD não entregou o documento (conexão fechada, erro HTTP ou não-PDF)."""


def caminho_cache(documento: Documento, cache: Path) -> Path:
    # O protocolo já é único e só tem caracteres seguros para nome de arquivo.
    return cache / f"{documento.protocolo}.pdf"


def _parece_pdf(conteudo: bytes) -> bool:
    return conteudo[:5] == b"%PDF-"


def baixar(documento: Documento, cache: Path) -> Path:
    """Baixa um documento se ainda não estiver em cache; devolve o caminho.

    Levanta DownloadRecusado em vez de gravar lixo: o RAD às vezes responde
    200 com uma página HTML de erro, e um HTML gravado como .pdf só quebra
    mais adiante, na extração, longe da causa.
    """
    cache.mkdir(parents=True, exist_ok=True)
    destino = caminho_cache(documento, cache)
    if destino.exists() and destino.stat().st_size > 0:
        return destino

    pedido = urllib.request.Request(documento.url, headers=fontes.CABECALHOS_RAD)
    try:
        with urllib.request.urlopen(pedido, timeout=120) as resposta:
            conteudo = resposta.read(LIMITE_BYTES + 1)
    except (urllib.error.URLError, ConnectionError, TimeoutError) as erro:
        raise DownloadRecusado(f"{documento.protocolo}: {erro}") from erro

    if len(conteudo) > LIMITE_BYTES:
        raise DownloadRecusado(f"{documento.protocolo}: passa de {LIMITE_BYTES} bytes")
    if not _parece_pdf(conteudo):
        # Quase sempre é a página de erro do RAD servida com status 200.
        raise DownloadRecusado(f"{documento.protocolo}: resposta não é PDF")

    destino.write_bytes(conteudo)
    return destino
