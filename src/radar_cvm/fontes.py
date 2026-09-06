"""Endereços e convenções do portal de dados abertos da CVM.

Tudo que sabemos sobre o formato da CVM mora aqui, para que uma mudança no
portal seja um patch num arquivo só.
"""

from __future__ import annotations

# O portal publica um ZIP por ano com o índice de todos os documentos
# eventuais e periódicos (IPE) entregues pelas companhias abertas.
URL_INDICE_IPE = (
    "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{ano}.zip"
)

# O CSV vem em latin-1 com separador ";" — não é UTF-8, e ler como UTF-8
# falha silenciosamente em acentos.
ENCODING_CSV = "latin-1"
SEPARADOR_CSV = ";"

# O RAD (onde ficam os PDFs) fecha a conexão sem responder quando o
# User-Agent não é de navegador: `curl` puro recebe "connection reset",
# não um 403. Verificado em 2026-09-06 contra um fato relevante do
# Banco do Brasil.
CABECALHOS_RAD = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
}

# Categorias do campo `Categoria` do índice. São os documentos em que uma
# decisão de investimento costuma se apoiar; o índice tem outras (Assembleia,
# Reunião da Administração) que são ruído para esta pergunta.
CATEGORIAS_RELEVANTES = (
    "Fato Relevante",
    "Comunicado ao Mercado",
    "Aviso aos Acionistas",
)
