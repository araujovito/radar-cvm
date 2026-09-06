"""Download dos PDFs no RAD, com cache em disco.

O RAD é o sistema da CVM que serve os documentos em si. Ele é mais frágil que
o portal de dados abertos: exige User-Agent de navegador e não devolve erro
HTTP quando recusa — fecha a conexão.
"""

from __future__ import annotations

import random
import time
import urllib.error
import urllib.request
from pathlib import Path

from radar_cvm import fontes
from radar_cvm.ingest.indice import Documento

# Um PDF de fato relevante tem tipicamente 100-400 KB. Nada perto de 20 MB é
# um documento normal, e baixar um anexo gigante trava a ingestão por um
# item só.
LIMITE_BYTES = 20 * 1024 * 1024

# Pausa entre downloads. O corpus tem 7.138 documentos nas categorias
# indexadas; sem pausa isso é uma rajada contra um serviço público que não
# pediu para participar. Meio segundo põe a ingestão completa em ~1 hora, que
# é aceitável para algo que se roda uma vez.
PAUSA_SEGUNDOS = 0.5

# O RAD falha de forma intermitente sob carga. Três tentativas com recuo
# exponencial e jitter cobrem a falha passageira sem insistir num documento
# que realmente não existe.
TENTATIVAS = 3
RECUO_BASE = 2.0


class DownloadRecusado(RuntimeError):
    """O RAD não entregou o documento (conexão fechada, erro HTTP ou não-PDF)."""


def caminho_cache(documento: Documento, cache: Path) -> Path:
    # O protocolo já é único e só tem caracteres seguros para nome de arquivo.
    return cache / f"{documento.protocolo}.pdf"


def _parece_pdf(conteudo: bytes) -> bool:
    return conteudo[:5] == b"%PDF-"


def _buscar_bytes(documento: Documento) -> bytes:
    """Uma tentativa de download, com recuo exponencial e jitter entre elas.

    O jitter não é preciosismo: sem ele, várias execuções que falham juntas
    voltam a bater no mesmo instante e reproduzem a rajada que o recuo
    deveria evitar.
    """
    pedido = urllib.request.Request(documento.url, headers=fontes.CABECALHOS_RAD)
    ultimo: Exception | None = None

    for tentativa in range(TENTATIVAS):
        if tentativa:
            time.sleep(RECUO_BASE**tentativa + random.uniform(0, 1))
        try:
            with urllib.request.urlopen(pedido, timeout=120) as resposta:
                return resposta.read(LIMITE_BYTES + 1)
        except urllib.error.HTTPError as erro:
            # 404 e 403 não melhoram com insistência; erro de servidor pode.
            if erro.code < 500:
                raise DownloadRecusado(f"{documento.protocolo}: HTTP {erro.code}") from erro
            ultimo = erro
        except (urllib.error.URLError, ConnectionError, TimeoutError) as erro:
            ultimo = erro

    raise DownloadRecusado(f"{documento.protocolo}: {TENTATIVAS} tentativas — {ultimo}")


def baixar(documento: Documento, cache: Path, *, pausa: float = PAUSA_SEGUNDOS) -> Path:
    """Baixa um documento se ainda não estiver em cache; devolve o caminho.

    Levanta DownloadRecusado em vez de gravar lixo: o RAD às vezes responde
    200 com uma página HTML de erro, e um HTML gravado como .pdf só quebra
    mais adiante, na extração, longe da causa.

    A pausa vale só quando há download de fato. Documento em cache não
    consome cota de ninguém, e pausar por ele tornaria a retomada tão lenta
    quanto a primeira ingestão — que é exatamente o que a retomada existe
    para evitar.
    """
    cache.mkdir(parents=True, exist_ok=True)
    destino = caminho_cache(documento, cache)
    if destino.exists() and destino.stat().st_size > 0:
        return destino

    conteudo = _buscar_bytes(documento)
    if pausa:
        time.sleep(pausa)

    if len(conteudo) > LIMITE_BYTES:
        raise DownloadRecusado(f"{documento.protocolo}: passa de {LIMITE_BYTES} bytes")
    if not _parece_pdf(conteudo):
        # Quase sempre é a página de erro do RAD servida com status 200.
        raise DownloadRecusado(f"{documento.protocolo}: resposta não é PDF")

    destino.write_bytes(conteudo)
    return destino
