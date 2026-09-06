"""O índice IPE é a fonte de tudo; estes testes fixam o que a CVM entrega."""

from radar_cvm.ingest.indice import Documento, ler_csv

CABECALHO = (
    "CNPJ_Companhia;Nome_Companhia;Codigo_CVM;Data_Referencia;Categoria;Tipo;"
    "Especie;Assunto;Data_Entrega;Tipo_Apresentacao;Protocolo_Entrega;Versao;Link_Download"
)


def _csv(*linhas: str) -> str:
    return "\n".join([CABECALHO, *linhas])


def test_le_uma_linha_completa():
    texto = _csv(
        "00.000.000/0001-91;BANCO DO BRASIL S.A.;1023;2026-01-19;Fato Relevante;;;"
        "Payout 2026;2026-01-19;Original;PROT-1;1;https://rad.cvm.gov.br/doc?p=1"
    )
    (doc,) = list(ler_csv(texto))
    assert doc == Documento(
        protocolo="PROT-1",
        empresa="BANCO DO BRASIL S.A.",
        cnpj="00.000.000/0001-91",
        categoria="Fato Relevante",
        assunto="Payout 2026",
        data_entrega="2026-01-19",
        url="https://rad.cvm.gov.br/doc?p=1",
    )


def test_descarta_linha_sem_link():
    """Entregas sem documento publicado existem no índice e não são baixáveis."""
    texto = _csv(
        "00.000.000/0001-91;EMPRESA X;1;2026-01-01;Fato Relevante;;;Assunto;"
        "2026-01-01;Original;PROT-2;1;"
    )
    assert list(ler_csv(texto)) == []


def test_data_entrega_perde_a_hora():
    """A CVM às vezes entrega data com hora; a citação só precisa do dia."""
    texto = _csv(
        "0;EMPRESA Y;1;2026-01-01;Fato Relevante;;;Assunto;"
        "2026-03-04 18:22:00;Original;PROT-3;1;https://rad.cvm.gov.br/doc?p=3"
    )
    (doc,) = list(ler_csv(texto))
    assert doc.data_entrega == "2026-03-04"
