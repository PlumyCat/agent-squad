# Codex Squad DOX

## Purpose

- Codex Squad orchestre des workers Codex ou Claude dans des sessions tmux, avec contextes de role et suivi par tickets.
- Le depot contient les wrappers, CLIs, skills Codex, roles, guides et scripts necessaires au workflow orchestrateur -> workers.

## Ownership

- Le `AGENTS.md` racine porte les regles globales du projet et l'index des zones durables.
- Aucun `AGENTS.md` enfant n'est defini pour le moment ; les regles de ce fichier s'appliquent a tout le depot.

## Local Contracts

- Les skills Codex installables vivent dans `skills/squad-*` et leur `name` de frontmatter doit rester aligné avec le nom du dossier.
- Le CLI worker principal est exposé par `./squad` et implémenté dans `claude-cli/main.py`.
- Les roles worker et orchestrateur vivent dans `context-cli/roles/`.
- Les tickets locaux restent dans `tickets-cli/tickets/` et sont manipules via `./tickets`.
- Les scripts de lancement de l'orchestrateur doivent privilegier `restart-squad-orchestrator.sh`.

## Work Guidance

- Preserver les changements existants du worktree : le depot sert souvent de configuration vivante.
- Garder les noms publics coherents avec la marque `squad` pour les skills, commandes slash et documentation active.
- Les noms automatiques de workers doivent rester compatibles tmux et conserver le prefixe d'agent (`codex-` ou `claude-`) pour le filtrage.
- Ne modifier les stories historiques dans `docs/stories/` que si la demande porte explicitement sur leur contenu.

## Verification

- Pour un changement CLI, executer au minimum `python -m compileall claude-cli context-cli tickets-cli`.
- Pour un changement de skills, verifier que `install-skills.sh` liste et copie les dossiers attendus.
- Pour un changement documentaire seul, une recherche `rg` ciblee suffit.

## Child DOX Index

- `claude-cli/` : CLI Python de gestion des workers tmux, expose par `./squad`.
- `context-cli/` : generation et validation des roles/directives.
- `tickets-cli/` : suivi local des taches deleguees.
- `skills/` : skills Codex installables, prefixes `squad-*`.
- `docs/` : guides actifs et stories historiques.
- `signals/` : fichiers de coordination waiting/responses entre orchestrateur et workers.
- `.squad-runs/` : scripts generes par session, non destines a etre edites manuellement.
