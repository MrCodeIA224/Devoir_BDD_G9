#!/usr/bin/env bash
# =============================================================================
# Génère le keyfile utilisé pour l'authentification interne du cluster
# (communication mongod <-> mongod <-> mongos), obligatoire dès que
# security.authorization=enabled sur un cluster shardé/replica set.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

KEYFILE="mongo-cluster.key"

if [ -f "$KEYFILE" ]; then
  echo "[!] $KEYFILE existe déjà — suppression pour régénération."
  rm -f "$KEYFILE"
fi

# 756 bits de hasard encodés en base64, format recommandé par MongoDB
openssl rand -base64 756 > "$KEYFILE"

# Permissions strictes : seul le propriétaire peut lire/écrire.
# mongod refuse de démarrer si le keyfile est trop permissif.
chmod 600 "$KEYFILE"

echo "[OK] Keyfile généré : $(pwd)/$KEYFILE"
echo "     -> Ne jamais committer ce fichier dans Git (voir .gitignore)."
