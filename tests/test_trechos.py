"""A divisão em trechos é onde a citação pode se perder silenciosamente."""

from radar_cvm.index.trechos import dividir_documento
from radar_cvm.ingest.indice import Documento
from radar_cvm.ingest.texto import Pagina

DOC = Documento(
    protocolo="PROT-1",
    empresa="EMPRESA X S.A.",
    cnpj="0",
    categoria="Fato Relevante",
    assunto="Assunto",
    data_entrega="2026-01-19",
    url="https://exemplo",
)


def test_todo_trecho_guarda_a_pagina_de_origem():
    paginas = [Pagina(1, "Primeira página."), Pagina(7, "Sétima página.")]
    trechos = dividir_documento(DOC, paginas)
    assert [t.pagina for t in trechos] == [1, 7]


def test_citacao_traz_empresa_categoria_data_e_pagina():
    (trecho,) = dividir_documento(DOC, [Pagina(3, "Texto.")])
    assert trecho.citacao == "EMPRESA X S.A. — Fato Relevante de 2026-01-19, p. 3"


def test_pagina_longa_vira_varios_trechos_com_sobreposicao():
    corpo = ". ".join(f"Frase numero {i} com algum conteudo de enchimento" for i in range(120))
    trechos = dividir_documento(DOC, [Pagina(1, corpo)], alvo=500, sobreposicao=100)
    assert len(trechos) > 1
    assert all(t.pagina == 1 for t in trechos)
    # A sobreposição precisa existir de fato, senão uma frase cortada ao meio
    # some do índice.
    assert trechos[0].texto[-40:] in trechos[1].texto


def test_pagina_vazia_nao_gera_trecho():
    assert dividir_documento(DOC, [Pagina(1, "   ")]) == []
