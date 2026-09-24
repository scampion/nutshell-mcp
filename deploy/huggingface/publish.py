#!/usr/bin/env python3
"""Publie sur Hugging Face : (1) le dataset de données, (2) le code du Space Docker.

Prérequis : `pip install huggingface_hub` et `hf auth login` (ou HF_TOKEN).
Usage :
    python deploy/huggingface/publish.py --user monuser --data-dir /chemin/vers/racine-donnees \\
        [--private-dataset] [--only dataset|space] [--dry-run]

`--data-dir` doit contenir `mirror/` et `eurostat.db` (par défaut : la racine du dépôt).
Le Space a besoin de la variable NUTSHELL_DATASET (posée ici) ; pour un dataset privé,
ajoutez un secret HF_TOKEN dans les réglages du Space.
"""
import argparse
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True, help="utilisateur ou organisation HF")
    ap.add_argument("--dataset-name", default="nutshell-data")
    ap.add_argument("--space-name", default="nutshell-mcp")
    ap.add_argument("--data-dir", type=Path, default=ROOT)
    ap.add_argument("--private-dataset", action="store_true")
    ap.add_argument("--only", choices=["dataset", "space"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    dataset_id = f"{a.user}/{a.dataset_name}"
    space_id = f"{a.user}/{a.space_name}"
    api = HfApi()

    if a.only in (None, "dataset"):
        for need in ("mirror", "eurostat.db"):
            if not (a.data_dir / need).exists():
                raise SystemExit(f"{a.data_dir / need} introuvable.")
        print(f"Dataset {dataset_id} <- {a.data_dir} (mirror/, eurostat.db)")
        if not a.dry_run:
            api.create_repo(dataset_id, repo_type="dataset", private=a.private_dataset, exist_ok=True)
            api.upload_folder(
                repo_id=dataset_id, repo_type="dataset", folder_path=a.data_dir,
                allow_patterns=["mirror/**", "eurostat.db"],
                ignore_patterns=["mirror/**/.tmp*", "**/*.tmp"],
                commit_message="Données nutshell-mcp",
            )

    if a.only in (None, "space"):
        print(f"Space {space_id} <- code + Dockerfile")
        if not a.dry_run:
            api.create_repo(space_id, repo_type="space", space_sdk="docker", exist_ok=True)
            api.add_space_variable(space_id, "NUTSHELL_DATASET", dataset_id)
            for path in ("pyproject.toml", "LICENSE"):
                api.upload_file(path_or_fileobj=ROOT / path, path_in_repo=path,
                                repo_id=space_id, repo_type="space")
            api.upload_file(path_or_fileobj=HERE / "README.space.md", path_in_repo="README.md",
                            repo_id=space_id, repo_type="space")
            api.upload_file(path_or_fileobj=HERE / "Dockerfile", path_in_repo="Dockerfile",
                            repo_id=space_id, repo_type="space")
            api.upload_file(path_or_fileobj=HERE / "bootstrap.py", path_in_repo="bootstrap.py",
                            repo_id=space_id, repo_type="space")
            for folder in ("nutshell_mcp", "registry"):
                api.upload_folder(repo_id=space_id, repo_type="space", folder_path=ROOT / folder,
                                  path_in_repo=folder, ignore_patterns=["__pycache__", "*.pyc"])
        print(f"URL MCP : https://{a.user}-{a.space_name}.hf.space/mcp")


if __name__ == "__main__":
    main()
