"""Quebra do texto em trechos buscáveis.

Um trecho carrega de onde veio (documento e página). Essa é a unidade que a
busca devolve e que o agente cita — se o trecho perde a origem, a citação
vira alegação.
"""

from __future__ import annotations

import dataclasses
import re

from radar_cvm.ingest.indice import Documento
from radar_cvm.ingest.texto import Pagina

# Alvo em caracteres, não em tokens: a métrica exata não importa aqui, e
# contar tokens exigiria uma dependência só para isso.
TAMANHO_ALVO = 1200
SOBREPOSICAO = 200


@dataclasses.dataclass(frozen=True, slots=True)
class Trecho:
    protocolo: str
    empresa: str
    categoria: str
    data_entrega: str
    pagina: int
    texto: str

    @property
    def citacao(self) -> str:
        return f"{self.empresa} — {self.categoria} de {self.data_entrega}, p. {self.pagina}"


def _dividir(texto: str, alvo: int, sobreposicao: int) -> list[str]:
    """Quebra em pedaços de ~alvo caracteres, cortando em fronteira de frase.

    A sobreposição existe porque um fato relevante costuma enunciar o valor
    numa frase e a condição na seguinte; cortar entre as duas produz um
    trecho que responde errado sem parecer errado.
    """
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) <= alvo:
        return [texto] if texto else []

    pedacos: list[str] = []
    inicio = 0
    while inicio < len(texto):
        fim = min(inicio + alvo, len(texto))
        if fim < len(texto):
            # Recua até o fim de frase mais próximo, se houver um razoavelmente perto.
            corte = texto.rfind(". ", inicio + alvo // 2, fim)
            if corte != -1:
                fim = corte + 1
        pedacos.append(texto[inicio:fim].strip())
        if fim >= len(texto):
            break
        inicio = max(fim - sobreposicao, inicio + 1)
    return [p for p in pedacos if p]


def dividir_documento(
    documento: Documento,
    paginas: list[Pagina],
    *,
    alvo: int = TAMANHO_ALVO,
    sobreposicao: int = SOBREPOSICAO,
) -> list[Trecho]:
    """Transforma as páginas de um documento em trechos com origem."""
    trechos = []
    for pagina in paginas:
        for pedaco in _dividir(pagina.texto, alvo, sobreposicao):
            trechos.append(
                Trecho(
                    protocolo=documento.protocolo,
                    empresa=documento.empresa,
                    categoria=documento.categoria,
                    data_entrega=documento.data_entrega,
                    pagina=pagina.numero,
                    texto=pedaco,
                )
            )
    return trechos
