"""O agente: responde perguntas sobre o corpus da CVM citando a fonte.

A regra que organiza o desenho: o modelo não tem acesso ao corpus a não ser
pelas ferramentas. Ele não recebe os documentos no prompt e não pode responder
de memória sobre uma empresa — se a busca não trouxer nada, a resposta correta
é dizer que não encontrou. É assim que a alucinação deixa de ser algo a
"mitigar por prompt" e passa a ser algo que a arquitetura torna difícil.
"""

from __future__ import annotations

import json

import anthropic
from anthropic import beta_tool

from radar_cvm.index.busca import Indice

MODELO = "claude-opus-5"

INSTRUCOES = """\
Você responde perguntas sobre documentos entregues à CVM por companhias abertas \
brasileiras (fatos relevantes, comunicados ao mercado e avisos aos acionistas).

Regras, em ordem de prioridade:

1. Toda afirmação de fato vem de um trecho devolvido por uma ferramenta. Você não \
sabe nada sobre essas empresas fora do que as ferramentas trouxerem nesta conversa.
2. Cite a fonte ao lado da afirmação, no formato que o próprio trecho traz em \
`citacao` — empresa, categoria, data e página.
3. Se a busca não trouxer trecho que sustente a resposta, diga que não encontrou e \
diga o que procurou. Não complete a lacuna com conhecimento geral, não estime e não \
generalize a partir de outra empresa.
4. Se os trechos se contradizem, aponte a contradição em vez de escolher um lado.
5. Números (valores, datas, percentuais) são transcritos do trecho, nunca recalculados \
ou arredondados.

Busque mais de uma vez com termos diferentes antes de concluir que algo não existe: \
o vocabulário do documento costuma ser mais formal que o da pergunta \
("grupamento" e não "agrupamento de ações", "juros sobre capital próprio" e não "JCP").\
"""


def _ferramentas(indice: Indice):
    """Cria as ferramentas ligadas a um índice.

    São fechamentos sobre `indice` em vez de funções de módulo com estado
    global: assim os testes montam um índice pequeno e nada precisa ser
    desmontado depois.
    """

    @beta_tool
    def buscar_documentos(pergunta: str, limite: int = 5) -> str:
        """Busca trechos de documentos da CVM que respondam a uma pergunta.

        Args:
            pergunta: Termos de busca. Use o vocabulário formal do documento.
            limite: Quantos trechos devolver, de 1 a 15.
        """
        limite = max(1, min(int(limite), 15))
        achados = indice.buscar(pergunta, limite=limite)
        if not achados:
            return json.dumps({"trechos": [], "aviso": "Nenhum trecho encontrado."})
        return json.dumps(
            {
                "trechos": [
                    {
                        "protocolo": r.trecho.protocolo,
                        "citacao": r.trecho.citacao,
                        "texto": r.trecho.texto,
                    }
                    for r in achados
                ]
            },
            ensure_ascii=False,
        )

    @beta_tool
    def ler_documento(protocolo: str) -> str:
        """Lê um documento inteiro, em ordem de página, pelo seu protocolo.

        Use quando um trecho da busca parecer incompleto e o contexto ao redor
        for necessário para responder com precisão.

        Args:
            protocolo: O campo `protocolo` de um trecho devolvido pela busca.
        """
        trechos = indice.por_protocolo(protocolo)
        if not trechos:
            return json.dumps({"erro": f"Protocolo {protocolo} não está no índice."})
        return json.dumps(
            {
                "citacao": trechos[0].citacao,
                "paginas": [{"pagina": t.pagina, "texto": t.texto} for t in trechos],
            },
            ensure_ascii=False,
        )

    return [buscar_documentos, ler_documento]


def responder(
    pergunta: str,
    indice: Indice,
    *,
    cliente: anthropic.Anthropic | None = None,
    modelo: str = MODELO,
) -> str:
    """Roda o agente até ele terminar e devolve o texto da resposta final."""
    cliente = cliente or anthropic.Anthropic()

    corredor = cliente.beta.messages.tool_runner(
        model=modelo,
        max_tokens=16000,
        system=INSTRUCOES,
        thinking={"type": "adaptive"},
        tools=_ferramentas(indice),
        messages=[{"role": "user", "content": pergunta}],
    )

    ultima = None
    for mensagem in corredor:
        ultima = mensagem

    if ultima is None:
        return "O agente terminou sem produzir resposta."
    if ultima.stop_reason == "refusal":
        return "O modelo recusou a pergunta."
    return "\n".join(b.text for b in ultima.content if b.type == "text").strip()
