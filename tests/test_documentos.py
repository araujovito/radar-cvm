"""O download é onde o RAD é hostil; estas são as regras de convivência."""

import urllib.error

import pytest

from radar_cvm.ingest import documentos
from radar_cvm.ingest.indice import Documento

DOC = Documento(
    protocolo="PROT-1",
    empresa="EMPRESA X",
    cnpj="0",
    categoria="Fato Relevante",
    assunto="Assunto",
    data_entrega="2026-01-19",
    url="https://rad.cvm.gov.br/doc?p=1",
)


def test_cache_evita_download_e_pausa(tmp_path, monkeypatch):
    """Documento em cache não consome cota; pausar por ele tornaria a
    retomada tão lenta quanto a primeira ingestão."""
    (tmp_path / "PROT-1.pdf").write_bytes(b"%PDF-1.7 conteudo")
    monkeypatch.setattr(documentos, "_buscar_bytes", lambda d: pytest.fail("baixou de novo"))
    monkeypatch.setattr(documentos.time, "sleep", lambda s: pytest.fail("pausou à toa"))
    assert documentos.baixar(DOC, tmp_path) == tmp_path / "PROT-1.pdf"


def test_resposta_que_nao_e_pdf_falha_alto(tmp_path, monkeypatch):
    """O RAD serve página de erro com status 200; gravá-la como .pdf só
    quebraria depois, na extração, longe da causa."""
    monkeypatch.setattr(documentos, "_buscar_bytes", lambda d: b"<html>erro</html>")
    monkeypatch.setattr(documentos.time, "sleep", lambda s: None)
    with pytest.raises(documentos.DownloadRecusado, match="não é PDF"):
        documentos.baixar(DOC, tmp_path)
    assert not (tmp_path / "PROT-1.pdf").exists()


def test_erro_do_cliente_nao_e_repetido(monkeypatch):
    """404 não melhora com insistência; repetir só gasta cota."""
    chamadas = []

    def falhar(pedido, timeout):
        chamadas.append(1)
        raise urllib.error.HTTPError(DOC.url, 404, "Not Found", {}, None)

    monkeypatch.setattr(documentos.urllib.request, "urlopen", falhar)
    monkeypatch.setattr(documentos.time, "sleep", lambda s: None)
    with pytest.raises(documentos.DownloadRecusado, match="404"):
        documentos._buscar_bytes(DOC)
    assert len(chamadas) == 1


def test_erro_de_servidor_e_repetido_ate_o_limite(monkeypatch):
    """500 costuma ser passageiro; é o caso em que insistir faz sentido."""
    chamadas = []

    def falhar(pedido, timeout):
        chamadas.append(1)
        raise urllib.error.HTTPError(DOC.url, 503, "Unavailable", {}, None)

    monkeypatch.setattr(documentos.urllib.request, "urlopen", falhar)
    monkeypatch.setattr(documentos.time, "sleep", lambda s: None)
    with pytest.raises(documentos.DownloadRecusado, match="tentativas"):
        documentos._buscar_bytes(DOC)
    assert len(chamadas) == documentos.TENTATIVAS
