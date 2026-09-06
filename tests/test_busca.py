"""BM25 sobre um corpus mínimo: o que a busca precisa acertar."""

import pytest

from radar_cvm.index.busca import Indice, normalizar
from radar_cvm.index.trechos import Trecho


def _trecho(protocolo: str, texto: str, pagina: int = 1, empresa: str = "EMPRESA X") -> Trecho:
    return Trecho(
        protocolo=protocolo,
        empresa=empresa,
        categoria="Fato Relevante",
        data_entrega="2026-01-19",
        pagina=pagina,
        texto=texto,
    )


@pytest.fixture
def indice() -> Indice:
    return Indice(
        [
            _trecho("A", "A Companhia aprovou o pagamento de juros sobre capital proprio."),
            _trecho("B", "A Companhia comunica o grupamento de acoes na proporcao de 10 para 1."),
            _trecho("C", "Programa de recompra de acoes de emissao propria.", pagina=2),
        ]
    )


def test_normalizar_remove_acento_e_palavra_vazia():
    assert normalizar("A Companhia e as ações") == ["acoes"]


def test_busca_traz_o_trecho_certo_no_topo(indice):
    (primeiro, *_) = indice.buscar("grupamento de acoes")
    assert primeiro.trecho.protocolo == "B"


def test_busca_casa_mesmo_com_acento_na_pergunta(indice):
    """O PDF perde acento na extração; a pergunta do usuário não."""
    (primeiro, *_) = indice.buscar("juros sobre capital próprio")
    assert primeiro.trecho.protocolo == "A"


def test_pergunta_sem_correspondencia_devolve_vazio(indice):
    assert indice.buscar("debenture conversivel em criptomoeda") == []


def test_indice_vazio_nao_quebra():
    assert Indice([]).buscar("qualquer coisa") == []


def test_por_protocolo_devolve_em_ordem_de_pagina():
    indice = Indice([_trecho("A", "segunda", pagina=2), _trecho("A", "primeira", pagina=1)])
    assert [t.pagina for t in indice.por_protocolo("A")] == [1, 2]


def test_ida_e_volta_pelo_disco_preserva_os_trechos(indice, tmp_path):
    caminho = tmp_path / "indice.json"
    indice.salvar(caminho)
    recarregado = Indice.carregar(caminho)
    assert len(recarregado) == len(indice)
    assert recarregado.buscar("grupamento")[0].trecho.protocolo == "B"
