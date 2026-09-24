# Space Docker : serveur MCP nutshell-mcp (HTTP streamable, offline) sur le port 7860.
# Les données (mirror/ + eurostat.db) sont téléchargées au démarrage depuis un HF Dataset.
FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=http \
    NUTSHELL_OFFLINE=1 \
    NUTSHELL_HTTP_HOST=0.0.0.0 \
    NUTSHELL_HTTP_PORT=7860 \
    NUTSHELL_DATA_DIR=/home/user/data

WORKDIR /home/user/app
COPY --chown=user pyproject.toml README.md LICENSE ./
COPY --chown=user nutshell_mcp ./nutshell_mcp
COPY --chown=user registry ./registry
COPY --chown=user bootstrap.py ./bootstrap.py
RUN pip install --no-cache-dir . huggingface_hub

EXPOSE 7860
CMD ["python", "bootstrap.py"]
