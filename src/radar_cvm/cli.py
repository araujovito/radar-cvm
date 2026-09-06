"""Linha de comando do radar-cvm."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from radar_cvm.index.busca import Indice
from radar_cvm.index.trechos import dividir_documento
from radar_cvm.ingest import documentos as baixador
from radar_cvm.ingest import indice as catalogo
from radar_cvm.ingest import progresso
from radar_cvm.ingest import texto as extrator

RAIZ_PADRAO = Path("data")


def _construir(args: argparse.Namespace) -> int:
    """Baixa, extrai e indexa. É a etapa cara; roda uma vez por corpus."""
    raiz = Path(args.dados)
    cache = raiz / "cache"

    csv_local = catalogo.baixar_indice(args.ano, raiz)
    docs = catalogo.carregar(csv_local, empresa=args.empresa)
    if args.limite:
        docs = docs[: args.limite]
    print(f"{len(docs)} documentos selecionados de {args.ano}", file=sys.stderr)

    extraidos = raiz / "trechos"
    trechos = []
    recusados = 0
    retomados = 0
    for i, doc in enumerate(docs, start=1):
        ja_feito = progresso.ler(doc.protocolo, extraidos)
        if ja_feito is not None:
            trechos.extend(ja_feito)
            retomados += 1
            continue
        try:
            pdf = baixador.baixar(doc, cache)
            paginas = extrator.extrair(pdf)
        except Exception as erro:  # noqa: BLE001
            # Um PDF corrompido não pode derrubar a ingestão inteira: o corpus
            # da CVM tem entregas malformadas e elas são a exceção esperada.
            recusados += 1
            print(f"  [pulado] {doc.protocolo}: {erro}", file=sys.stderr)
            continue
        novos = dividir_documento(doc, paginas)
        progresso.gravar(doc.protocolo, novos, extraidos)
        trechos.extend(novos)
        if i % 25 == 0:
            print(f"  {i}/{len(docs)} — {len(trechos)} trechos", file=sys.stderr)

    if retomados:
        print(f"  {retomados} documentos reaproveitados do cache", file=sys.stderr)

    indice = Indice(trechos)
    indice.salvar(raiz / "indice.json")
    print(
        f"Índice com {len(indice)} trechos de {len(docs) - recusados} documentos "
        f"({recusados} pulados) em {raiz / 'indice.json'}",
        file=sys.stderr,
    )
    return 0


def _buscar(args: argparse.Namespace) -> int:
    """Busca sem LLM — serve para conferir o índice antes de gastar token."""
    indice = Indice.carregar(Path(args.dados) / "indice.json")
    achados = indice.buscar(args.pergunta, limite=args.limite)
    if not achados:
        print("Nenhum trecho encontrado.")
        return 1
    for resultado in achados:
        print(f"\n[{resultado.escore:.2f}] {resultado.trecho.citacao}")
        print(f"  {resultado.trecho.texto[:300]}...")
    return 0


def _perguntar(args: argparse.Namespace) -> int:
    from radar_cvm.agent.agente import responder

    indice = Indice.carregar(Path(args.dados) / "indice.json")
    print(responder(args.pergunta, indice))
    return 0


def _avaliar(args: argparse.Namespace) -> int:
    """Mede o comportamento em vez de descrevê-lo."""
    import json

    from radar_cvm.avaliacao import executor

    indice = executor.montar_corpus(Path(args.dados))
    casos = executor.carregar_casos()
    print(f"{len(casos)} casos sobre {len(indice)} trechos", file=sys.stderr)

    notas = executor.executar(indice, casos)

    for nota in notas:
        marca = "!" if nota.erro else ("v" if nota.acertou else "x")
        extra = f"  orfaos={nota.orfaos}" if nota.orfaos else ""
        print(f"  [{marca}] {nota.caso.id:<20} {nota.caso.tipo:<12}{extra}", file=sys.stderr)

    resumo = executor.resumir(notas)
    if args.saida:
        Path(args.saida).write_text(
            json.dumps(
                {
                    "resumo": resumo,
                    "notas": [
                        {
                            "id": n.caso.id,
                            "tipo": n.caso.tipo,
                            "acertou": n.acertou,
                            "citou": n.citou,
                            "fatos_ok": n.fatos_ok,
                            "recusou": n.recusou,
                            "ancorado": n.ancorado,
                            "orfaos": n.orfaos,
                            "erro": n.erro,
                            "segundos": round(n.segundos, 1),
                            "resposta": n.resposta,
                        }
                        for n in notas
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0 if resumo["erros"] == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="radar",
        description="Agente que responde sobre documentos da CVM citando a fonte.",
    )
    parser.add_argument("--dados", default=str(RAIZ_PADRAO), help="Diretório de dados")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("construir", help="Baixa documentos da CVM e monta o índice")
    p.add_argument("--ano", type=int, default=2026)
    p.add_argument("--empresa", help="Filtra por nome da companhia (substring)")
    p.add_argument("--limite", type=int, help="Máximo de documentos, para testar rápido")
    p.set_defaults(func=_construir)

    p = sub.add_parser("buscar", help="Busca trechos no índice, sem chamar o modelo")
    p.add_argument("pergunta")
    p.add_argument("--limite", type=int, default=5)
    p.set_defaults(func=_buscar)

    p = sub.add_parser("perguntar", help="Pergunta ao agente")
    p.add_argument("pergunta")
    p.set_defaults(func=_perguntar)

    p = sub.add_parser("avaliar", help="Roda a avaliação sobre o corpus congelado")
    p.add_argument("--saida", help="Grava o resultado detalhado em JSON")
    p.set_defaults(func=_avaliar)

    args = parser.parse_args(argv)
    codigo: int = args.func(args)
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
