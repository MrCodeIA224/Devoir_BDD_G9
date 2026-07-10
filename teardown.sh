#!/bin/bash
# =============================================================================
# Arrête et nettoie le cluster Docker (conteneurs, réseaux et volumes).
# Usage : 
#   ./cleanup.sh     -> Arrête les conteneurs (conserve les données)
#   ./cleanup.sh -v  -> Supprime tout et réinitialise à zéro (efface les volumes)
# =============================================================================
set -euo pipefail

if [ "${1:-}" = "-v" ]; then
  echo -e "\033[0;31m[!] Suppression complète des conteneurs ET des bases de données locales...\033[0m"
  docker compose down -v
  # Optionnel : Nettoyer aussi les dossiers physiques locaux créés par ton init.sh
  # rm -rf data/config* data/shard*
else
  echo -e "\033[0;34mArrêt des conteneurs (les données médicales locales sont conservées).\033[0m"
  echo "👉 Utilisez './cleanup.sh -v' pour tout effacer et repartir à zéro."
  docker compose down
fi
