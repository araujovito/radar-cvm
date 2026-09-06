"""O corretor é o instrumento de medida; se ele mente, a métrica mente junto."""

from radar_cvm.avaliacao.corretores import ancorado, citou, recusou, trouxe_os_fatos


class TestCitou:
    def test_reconhece_as_formas_que_o_agente_produz(self):
        assert citou("conforme p. 3 do comunicado")
        assert citou("está na p.44")
        assert citou("ver página 12")
        assert citou("ver pagina 12")  # extração de PDF perde acento

    def test_resposta_sem_pagina_nao_conta_como_citacao(self):
        assert not citou("Segundo o comunicado do Banco do Brasil, o valor foi R$ 5,2 bi.")


class TestFatos:
    def test_exige_todos_os_valores(self):
        assert trouxe_os_fatos("R$ 5,2 bi e R$ 0,91 por acao", ["5,2", "0,91"])
        assert not trouxe_os_fatos("R$ 5,2 bi", ["5,2", "0,91"])

    def test_lista_vazia_passa(self):
        """Casos qualitativos não têm valor a conferir; quem julga é a citação."""
        assert trouxe_os_fatos("qualquer resposta", [])


class TestRecusou:
    def test_reconhece_a_recusa(self):
        assert recusou("Não encontrei documentos da Petrobras na base.")
        assert recusou("Nenhum trecho sustenta essa afirmação.")

    def test_recusa_com_numero_nao_conta(self):
        """'Não encontrei, mas o valor é 1,5' é alucinação com verniz de humildade."""
        assert not recusou("Não encontrei o documento, mas o lucro foi R$ 1,5 bilhão.")

    def test_resposta_afirmativa_nao_e_recusa(self):
        assert not recusou("O lucro do Itaú foi de 41 bilhões, conforme p. 2.")


class TestAncorado:
    def test_numero_presente_no_corpus_passa(self):
        ok, orfaos = ancorado("distribuiu R$ 5,2 bilhões", "em 2025 foram R$ 5,2 bilhões em JCP")
        assert ok and orfaos == []

    def test_numero_inventado_e_apontado(self):
        ok, orfaos = ancorado("o lucro foi R$ 9,9 bilhões", "o lucro foi R$ 3,4 bilhões")
        assert not ok and orfaos == ["9,9"]

    def test_separador_de_milhar_e_reconhecido(self):
        ok, _ = ancorado("são 5.730.834.040 ações", "total de 5.730.834.040 ações")
        assert ok

    def test_inteiro_curto_e_ignorado_de_proposito(self):
        """'30' casaria por acaso em qualquer documento; medir isso é ruído."""
        ok, orfaos = ancorado("o payout é de 30%", "corpus sem esse numero")
        assert ok and orfaos == []

    def test_resposta_sem_numero_passa(self):
        ok, _ = ancorado("Não encontrei nada sobre isso.", "qualquer corpus")
        assert ok
