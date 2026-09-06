"""A escolha de provedor é configuração; estes testes fixam as regras dela."""

import pytest

from radar_cvm.agent.provedor import ANTHROPIC, ZAI, escolher


def test_padrao_e_o_provedor_gratuito(monkeypatch):
    """O padrão precisa ser o gratuito: rodar o projeto não pode custar dinheiro."""
    monkeypatch.delenv("RADAR_PROVEDOR", raising=False)
    assert escolher() is ZAI


def test_variavel_de_ambiente_troca_o_provedor(monkeypatch):
    monkeypatch.setenv("RADAR_PROVEDOR", "anthropic")
    assert escolher() is ANTHROPIC


def test_argumento_tem_precedencia_sobre_a_variavel(monkeypatch):
    monkeypatch.setenv("RADAR_PROVEDOR", "anthropic")
    assert escolher("zai") is ZAI


def test_provedor_desconhecido_falha_dizendo_os_conhecidos(monkeypatch):
    monkeypatch.delenv("RADAR_PROVEDOR", raising=False)
    with pytest.raises(RuntimeError, match="zai"):
        escolher("gemini")


def test_chave_ausente_falha_nomeando_a_variavel(monkeypatch):
    """O erro precisa dizer QUAL variável falta, senão vira caça ao tesouro."""
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ZAI_API_KEY"):
        ZAI.cliente()
