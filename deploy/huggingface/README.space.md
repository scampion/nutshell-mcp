---
title: nutshell-mcp
emoji: 🇪🇺
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: agpl-3.0
short_description: Serveur MCP de données territoriales européennes (NUTS)
---

# nutshell-mcp

« Europe in a nutshell » : serveur MCP de données territoriales européennes (Eurostat, NUTS).

Endpoint MCP (HTTP streamable) : `https://<utilisateur>-<space>.hf.space/mcp`

Les données sont téléchargées au démarrage depuis le dataset défini par la variable `NUTSHELL_DATASET`
(le premier démarrage peut prendre quelques minutes). Code source : voir le dépôt du projet.
