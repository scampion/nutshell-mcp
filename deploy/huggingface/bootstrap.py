"""Démarrage du Space : télécharge les données depuis le HF Dataset, puis lance le serveur MCP.

Variables : ``NUTSHELL_DATASET`` (ex. ``user/nutshell-data``, obligatoire),
``HF_TOKEN`` (secret du Space, seulement si le dataset est privé),
``SPACE_HOST`` (fourni par HF) sert à autoriser le Host du Space.
"""
import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

data_dir = Path(os.environ["NUTSHELL_DATA_DIR"])
dataset = os.environ.get("NUTSHELL_DATASET")
if not dataset:
    sys.exit("NUTSHELL_DATASET non défini (variable du Space, ex. user/nutshell-data).")

print(f"Téléchargement des données depuis {dataset} vers {data_dir} …", flush=True)
snapshot_download(repo_id=dataset, repo_type="dataset", local_dir=data_dir)

hosts = [os.environ[k] for k in ("SPACE_HOST",) if os.environ.get(k)]
extra = os.environ.get("NUTSHELL_ALLOWED_HOSTS", "")
os.environ["NUTSHELL_ALLOWED_HOSTS"] = ",".join(filter(None, [extra, *hosts]))

os.execvp(sys.executable, [sys.executable, "-m", "nutshell_mcp.server"])
