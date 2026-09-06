# Imagem slim: o projeto não compila nada, e as dependências (pypdf, anthropic)
# são puro Python.
FROM python:3.13-slim

WORKDIR /app

# Copiar só o necessário para instalar antes do código-fonte mantém a camada
# de dependências em cache quando só o código muda.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# O índice e o cache de PDFs ficam num volume: são grandes, reprodutíveis e
# não pertencem à imagem.
VOLUME ["/app/data"]

ENTRYPOINT ["radar"]
CMD ["--help"]
