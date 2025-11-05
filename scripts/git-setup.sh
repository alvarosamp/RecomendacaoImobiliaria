#!/usr/bin/env bash
# Uso: bash scripts/git-setup.sh <remote-url>
# Ex.: bash scripts/git-setup.sh git@github.com:me/ImobiliariaNovo.git

set -euo pipefail

REMOTE_URL=${1:-}

# Inicializar repo local (se ainda não inicializado)
if [ ! -d .git ]; then
  git init
  git checkout -b main || git checkout -b master
fi

# Adicionar arquivos importantes primeiro (respeita .gitignore)
git add .gitignore
git add config/.env.example
git add LICENSE
git add Readme.md

# Adicionar tudo e commitar
git add .
git commit -m "chore: initial project layout and config"

# Se remote informado, adicionar e push
if [ -n "$REMOTE_URL" ]; then
  git remote add origin "$REMOTE_URL" || git remote set-url origin "$REMOTE_URL"
  git push -u origin HEAD
fi

# Recomendações adicionais (manuais):
cat <<'EOF'

Recomendações:
- Crie branches para features: git checkout -b feat/descrição
- Commits claros: tipo(scope): descrição (ex.: feat(api): adicionar endpoint /scores)
- Para abrir PRs com GitHub CLI:
  gh repo create OR gh pr create --base main --head <branch> --title "Título" --body "Descrição"
- Em Windows PowerShell (Git Bash não disponível), execute comandos equivalentes:
  git init
  git checkout -b main
  git add .
  git commit -m "chore: initial"
  git remote add origin <REMOTE_URL>
  git push -u origin main

EOF
