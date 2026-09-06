"""A retomada precisa distinguir 'não processei' de 'processei e deu vazio'."""

import json

from radar_cvm.index.trechos import Trecho
from radar_cvm.ingest import progresso

TRECHO = Trecho(
    protocolo="PROT-1",
    empresa="EMPRESA X",
    categoria="Fato Relevante",
    data_entrega="2026-01-19",
    pagina=1,
    texto="Texto do documento.",
)


def test_documento_nunca_visto_devolve_none(tmp_path):
    assert progresso.ler("PROT-1", tmp_path) is None


def test_ida_e_volta_preserva_o_trecho(tmp_path):
    progresso.gravar("PROT-1", [TRECHO], tmp_path)
    assert progresso.ler("PROT-1", tmp_path) == [TRECHO]


def test_lista_vazia_nao_se_confunde_com_ausencia(tmp_path):
    """PDF digitalizado gera zero trechos; sem isso ele seria reprocessado sempre."""
    progresso.gravar("PROT-1", [], tmp_path)
    assert progresso.ler("PROT-1", tmp_path) == []


def test_arquivo_truncado_e_descartado_em_vez_de_estourar(tmp_path):
    """Escrita interrompida no meio: reprocessar é barato, confiar não é."""
    (tmp_path / "PROT-1.json").write_text('[{"protocolo": "PROT-1"', encoding="utf-8")
    assert progresso.ler("PROT-1", tmp_path) is None
    assert not (tmp_path / "PROT-1.json").exists()


def test_gravacao_nao_deixa_arquivo_parcial(tmp_path):
    progresso.gravar("PROT-1", [TRECHO], tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["PROT-1.json"]
    json.loads((tmp_path / "PROT-1.json").read_text(encoding="utf-8"))
