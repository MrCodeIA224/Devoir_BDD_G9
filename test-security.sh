#!/bin/bash
# =============================================================================
# Suite de tests de sécurité automatisée pour la plateforme de logs médicaux.
# Aligné sur l'architecture et les variables de la Personne A.
# Chaque test affiche PASS si MongoDB bloque ou autorise correctement l'action.
# =============================================================================
set -uo pipefail

# Couleurs pour le terminal Ubuntu
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Récupération des mêmes variables que ton init.sh
APP_DB_NAME="hopital_db"
MEDECIN_USER="dr_diop"
MEDECIN_PASSWORD="MedecinPassword2026"
INFIRMIER_USER="inf_mbacke"
INFIRMIER_PASSWORD="InfirmierPassword2026"
LABORANTIN_USER="lab_ndiaye"
LABORANTIN_PASSWORD="LaborantinPassword2026"

PASS=0
FAIL=0

check() {
  local description="$1"
  local expected="$2"  # "should_succeed" | "should_fail"
  local actual_status="$3"
  if { [ "$expected" = "should_succeed" ] && [ "$actual_status" -eq 0 ]; } || \
     { [ "$expected" = "should_fail" ] && [ "$actual_status" -ne 0 ]; }; then
    echo -e "[${GREEN}PASS${NC}] $description"
    PASS=$((PASS+1))
  else
    echo -e "[${RED}FAIL${NC}] $description (code retour observé: $actual_status)"
    FAIL=$((FAIL+1))
  fi
}

echo "=== DÉMARRAGE DE LA SUITE DE TESTS DE SÉCURITÉ ==="

echo "== Test 1 : Connexion SANS authentification doit être REFUSÉE =="
docker exec -t mongo-mongos mongosh \
  --tls --tlsCAFile /etc/mongo-certs/ca.pem --tlsCertificateKeyFile /etc/mongo-certs/admin-client.pem \
  --port 27017 --quiet \
  --eval "db.getSiblingDB('${APP_DB_NAME}').dossiers_patients.find().toArray()" \
  > /dev/null 2>&1
check "Accès anonyme refusé par le cluster" "should_fail" $?

echo "== Test 2 : Connexion SANS chiffrer en TLS doit être REFUSÉE =="
docker exec -t mongo-mongos mongosh --port 27017 --quiet \
  --eval "db.runCommand({ping:1})" > /dev/null 2>&1
check "Accès sans chiffrement TLS bloqué (requireTLS)" "should_fail" $?

echo "== Test 3 : Le laborantin ne doit PAS pouvoir accéder aux dossiers cliniques =="
docker exec -t mongo-mongos mongosh \
  --tls --tlsCAFile /etc/mongo-certs/ca.pem --tlsCertificateKeyFile /etc/mongo-certs/admin-client.pem \
  --port 27017 --quiet \
  -u "${LABORANTIN_USER}" -p "${LABORANTIN_PASSWORD}" --authenticationDatabase "${APP_DB_NAME}" \
  --eval "db.getSiblingDB('${APP_DB_NAME}').dossiers_patients.find().toArray()" \
  > /dev/null 2>&1
check "role_laborantin n'a pas accès à dossiers_patients (Cloisonnement RBAC)" "should_fail" $?

echo "== Test 4 : Le laborantin DOIT pouvoir consulter les examens de laboratoire =="
docker exec -t mongo-mongos mongosh \
  --tls --tlsCAFile /etc/mongo-certs/ca.pem --tlsCertificateKeyFile /etc/mongo-certs/admin-client.pem \
  --port 27017 --quiet \
  -u "${LABORANTIN_USER}" -p "${LABORANTIN_PASSWORD}" --authenticationDatabase "${APP_DB_NAME}" \
  --eval "db.getSiblingDB('${APP_DB_NAME}').resultats_labo.find().toArray()" \
  > /dev/null 2>&1
check "role_laborantin accède légitimement à sa collection métier" "should_succeed" $?

echo "== Test 5 : L'infirmier ne doit PAS voir la collection brute dossiers_patients =="
docker exec -t mongo-mongos mongosh \
  --tls --tlsCAFile /etc/mongo-certs/ca.pem --tlsCertificateKeyFile /etc/mongo-certs/admin-client.pem \
  --port 27017 --quiet \
  -u "${INFIRMIER_USER}" -p "${INFIRMIER_PASSWORD}" --authenticationDatabase "${APP_DB_NAME}" \
  --eval "db.getSiblingDB('${APP_DB_NAME}').dossiers_patients.find().toArray()" \
  > /dev/null 2>&1
check "role_infirmier n'a pas de droit de lecture sur la collection source" "should_fail" $?

echo "== Test 6 : L'infirmier DOIT pouvoir lire la vue avec données masquées =="
docker exec -t mongo-mongos mongosh \
  --tls --tlsCAFile /etc/mongo-certs/ca.pem --tlsCertificateKeyFile /etc/mongo-certs/admin-client.pem \
  --port 27017 --quiet \
  -u "${INFIRMIER_USER}" -p "${INFIRMIER_PASSWORD}" --authenticationDatabase "${APP_DB_NAME}" \
  --eval "db.getSiblingDB('${APP_DB_NAME}').v_dossiers_patients_infirmier.find().toArray()" \
  > /dev/null 2>&1
check "role_infirmier accède bien à la vue filtrée (Data Masking)" "should_succeed" $?

echo "== Test 7 : Une tentative avec un mauvais mot de passe doit échouer =="
docker exec -t mongo-mongos mongosh \
  --tls --tlsCAFile /etc/mongo-certs/ca.pem --tlsCertificateKeyFile /etc/mongo-certs/admin-client.pem \
  --port 27017 --quiet \
  -u "${MEDECIN_USER}" -p "FauxMotDePasseAlerte" --authenticationDatabase "${APP_DB_NAME}" \
  --eval "db.runCommand({ping:1})" > /dev/null 2>&1
check "Authentification erronée rejetée par MongoDB" "should_fail" $?

echo "== Test 8 : Authentification forte par certificat x.509 (Compte Auditeur) =="
docker exec -t mongo-mongos mongosh \
  --tls --tlsCAFile /etc/mongo-certs/ca.pem --tlsCertificateKeyFile /etc/mongo-certs/client-auditeur.pem \
  --port 27017 --quiet \
  --authenticationMechanism MONGODB-X509 --authenticationDatabase '$external' \
  --eval "db.getSiblingDB('audit_db').access_logs.find().limit(1).toArray()" \
  > /dev/null 2>&1
check "Authentification x.509 de l'auditeur validée sans mot de passe" "should_succeed" $?

echo ""
echo "======================================================================"
echo -e "BILAN : $PASS test(s) validé(s), $FAIL test(s) en échec sur $((PASS+FAIL))"
echo "======================================================================"

[ "$FAIL" -eq 0 ]
