"""De onde vem o modelo.

O agente foi escrito contra o SDK da Anthropic, mas não está preso a ele: a
Z.ai serve os modelos GLM num endpoint que fala o mesmo protocolo. Trocar de
provedor é trocar URL base, chave e nome do modelo — não reescrever o laço de
ferramentas.

Isso mantém uma porta aberta que interessa ao projeto: o mesmo código roda
num modelo gratuito para desenvolver e iterar, e num modelo de fronteira para
comparar. A diferença entre os dois é uma variável de ambiente, o que torna a
comparação um experimento barato em vez de uma reescrita.
"""

from __future__ import annotations

import dataclasses
import os

import anthropic


@dataclasses.dataclass(frozen=True, slots=True)
class Provedor:
    nome: str
    modelo: str
    url_base: str | None
    variavel_chave: str

    def cliente(self) -> anthropic.Anthropic:
        chave = os.environ.get(self.variavel_chave)
        if not chave:
            raise RuntimeError(f"Provedor '{self.nome}' precisa da variável {self.variavel_chave}.")
        if self.url_base:
            return anthropic.Anthropic(api_key=chave, base_url=self.url_base)
        return anthropic.Anthropic(api_key=chave)


# GLM-4.7-Flash é o modelo gratuito da Z.ai — gratuito de fato, em entrada,
# saída e cache. Os "Flash" mais novos (5.3) são grátis só por promoção
# datada, o que não serve para um projeto que fica de pé por meses.
ZAI = Provedor(
    nome="zai",
    modelo="glm-4.7-flash",
    url_base="https://api.z.ai/api/anthropic",
    variavel_chave="ZAI_API_KEY",
)

ANTHROPIC = Provedor(
    nome="anthropic",
    modelo="claude-opus-5",
    url_base=None,
    variavel_chave="ANTHROPIC_API_KEY",
)

DISPONIVEIS = {p.nome: p for p in (ZAI, ANTHROPIC)}
PADRAO = "zai"


def escolher(nome: str | None = None) -> Provedor:
    """Resolve o provedor por argumento, depois por RADAR_PROVEDOR, depois padrão."""
    nome = nome or os.environ.get("RADAR_PROVEDOR") or PADRAO
    if nome not in DISPONIVEIS:
        conhecidos = ", ".join(sorted(DISPONIVEIS))
        raise RuntimeError(f"Provedor '{nome}' desconhecido. Conhecidos: {conhecidos}.")
    return DISPONIVEIS[nome]
