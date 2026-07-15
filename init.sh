#!/bin/bash
# =============================================================================
# Script d'initialisation global — Plateforme de Logs Médicaux (Dossier Patient Partagé)
# Gère les permissions, démarre l'infrastructure Docker et déploie la sécurité
# multi-niveaux (TLS / RBAC / Sharding / Profiling) dans l'ordre strict requis.
# =============================================================================

# Couleurs pour le terminal Ubuntu
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Définition des variables d'environnement (Alignées sur le travail de l'équipe)
APP_DB_NAME="hopital_db"
ROOT_USER="admin_root"
ROOT_PASSWORD="SuperSecretRootPassword2026"
DBA_USER="admin_infra_dba"
DBA_PASSWORD="SecureDBAPassword2026"

MEDECIN_USER="dr_diop"
MEDECIN_PASSWORD="MedecinPassword2026"
INFIRMIER_USER="inf_mbacke"
INFIRMIER_PASSWORD="InfirmierPassword2026"
LABORANTIN_USER="lab_ndiaye"
LABORANTIN_PASSWORD="LaborantinPassword2026"
ADMIN_HOPITAL_USER="admin_fonctionnel"
ADMIN_HOPITAL_PASSWORD="AdminHopitalPassword2026"
AUDITEUR_USER="auditeur_scram"
AUDITEUR_PASSWORD="AuditeurPassword2026"
APP_USER="audit_watcher_app"
APP_PASSWORD="WatcherAppPassword2026"

# Chaines d'injection de variables pour mongosh (--eval)
EVAL_SHARDS_VARIABLES="var SHARD_HOST=\"shard2\"; var SHARD_RS=\"shard2ReplSet\";"
EVAL_ADMIN_VARIABLES="var ROOT_USER=\"$ROOT_USER\"; var ROOT_PASSWORD=\"$ROOT_PASSWORD\"; var DBA_USER=\"$DBA_USER\"; var DBA_PASSWORD=\"$DBA_PASSWORD\";"
EVAL_APP_VARIABLES="var ROOT_USER=\"$ROOT_USER\"; var ROOT_PASSWORD=\"$ROOT_PASSWORD\"; var APP_DB_NAME=\"$APP_DB_NAME\";"
EVAL_USERS_VARIABLES="var ROOT_USER=\"$ROOT_USER\"; var ROOT_PASSWORD=\"$ROOT_PASSWORD\"; var APP_DB_NAME=\"$APP_DB_NAME\"; var MEDECIN_USER=\"$MEDECIN_USER\"; var MEDECIN_PASSWORD=\"$MEDECIN_PASSWORD\"; var INFIRMIER_USER=\"$INFIRMIER_USER\"; var INFIRMIER_PASSWORD=\"$INFIRMIER_PASSWORD\"; var LABORANTIN_USER=\"$LABORANTIN_USER\"; var LABORANTIN_PASSWORD=\"$LABORANTIN_PASSWORD\"; var ADMIN_HOPITAL_USER=\"$ADMIN_HOPITAL_USER\"; var ADMIN_HOPITAL_PASSWORD=\"$ADMIN_HOPITAL_PASSWORD\"; var AUDITEUR_USER=\"$AUDITEUR_USER\"; var AUDITEUR_PASSWORD=\"$AUDITEUR_PASSWORD\"; var APP_USER=\"$APP_USER\"; var APP_PASSWORD=\"$APP_PASSWORD\";"

# Raccourcis de connexion administratifs TLS locaux requis par net.tls.mode=requireTLS
MONGOSH_TLS_ADMIN="mongosh --tls --tlsCertificateKeyFile ./certs/admin-client.pem --tlsCAFile ./certs/ca.pem"

echo -e "${BLUE}=== [1/6] Alignement des permissions de sécurité Linux ===${NC}"
mkdir -p data/config1 data/config2 data/config3 data/shard1 data/shard1-node2 data/shard1-node3 data/shard2 data/shard3 data/shard4
chmod -R 777 data/
chmod 400 keyfile/mongo-cluster.key 2>/dev/null || echo -e "${RED}[!] Attention: keyfile introuvable${NC}"
chmod 600 certs/*.pem 2>/dev/null || echo -e "${RED}[!] Attention: Certificats PEM introuvables${NC}"
echo -e "${GREEN}[OK] Dossiers et permissions initialisés.${NC}\n"

echo -e "${BLUE}=== [2/6] Démarrage des conteneurs via Docker Compose ===${NC}"
docker compose up -d
echo -e "${YELLOW}Attente de 15 secondes pour l'initialisation des processus MongoDB 8.0...${NC}"
sleep 15

echo -e "${BLUE}=== [3/6] Initialisation logique de l'infrastructure de base ===${NC}"

echo "-> Liaison du Replica Set des Config Servers (Script 01)..."
docker exec -it mongo-config1 $MONGOSH_TLS_ADMIN --port 27019 --file /init/01-init-configsvr-rs.js
sleep 5

echo "-> Liaison spécifique du Shard 1 (3 membres pour la démo de cohérence)..."
docker exec -it mongo-shard1 $MONGOSH_TLS_ADMIN --port 27018 --eval '
  rs.initiate({
    _id: "shard1ReplSet",
    members: [
      { _id: 0, host: "shard1:27018" },
      { _id: 1, host: "shard1-node2:27018" },
      { _id: 2, host: "shard1-node3:27018" }
    ]
  })
'
sleep 5

echo "-> Liaison générique des Shards 2, 3 et 4 (Script 02)..."
docker exec -it mongo-shard2 $MONGOSH_TLS_ADMIN --port 27018 --eval 'var SHARD_HOST="shard2"; var SHARD_RS="shard2ReplSet";' --file /init/02-init-shard-rs.js
docker exec -it mongo-shard3 $MONGOSH_TLS_ADMIN --port 27018 --eval 'var SHARD_HOST="shard3"; var SHARD_RS="shard3ReplSet";' --file /init/02-init-shard-rs.js
docker exec -it mongo-shard4 $MONGOSH_TLS_ADMIN --port 27018 --eval 'var SHARD_HOST="shard4"; var SHARD_RS="shard4ReplSet";' --file /init/02-init-shard-rs.js
sleep 3

echo "-> Enregistrement des 4 fragments auprès du routeur central (Script 03)..."
docker exec -it mongo-mongos $MONGOSH_TLS_ADMIN --port 27017 --file /init/03-mongos-addshards.js
sleep 2

echo -e "${BLUE}=== [4/6] Création des comptes administratifs & Verrouillage du cluster ===${NC}"
echo "-> Déploiement des utilisateurs racine (Script 04)..."
docker exec -it mongo-mongos $MONGOSH_TLS_ADMIN --port 27017 --eval "$EVAL_ADMIN_VARIABLES" --file /init/04-create-admin-users.js
echo -e "${YELLOW}Localhost exception fermée. Authentification désormais obligatoire.${NC}\n"
sleep 2

echo -e "${BLUE}=== [5/6] Déploiement de la sécurité applicative et métier (RBAC) ===${NC}"

echo "-> Création des rôles métiers de l'hôpital (Script 05)..."
docker exec -it mongo-mongos $MONGOSH_TLS_ADMIN --port 27017 --eval "$EVAL_APP_VARIABLES" --file /init/05-rbac-roles.js

echo "-> Génération des comptes professionnels et du jeton X.509 (Script 06)..."
docker exec -it mongo-mongos $MONGOSH_TLS_ADMIN --port 27017 --eval "$EVAL_USERS_VARIABLES" --file /init/06-create-app-users.js

echo "-> Activation du Sharding sur le domaine médical (Script 07)..."
docker exec -it mongo-mongos $MONGOSH_TLS_ADMIN --port 27017 --eval "$EVAL_APP_VARIABLES" --file /init/07-sharding-collections.js

echo "-> Création des vues de masquage de données pour les infirmiers (Script 08)..."
docker exec -it mongo-mongos $MONGOSH_TLS_ADMIN --port 27017 --eval "$EVAL_APP_VARIABLES" --file /init/08-views-field-redaction.js

echo "-> Activation du Profiler d'audit et de traçabilité légale (Script 09)..."
docker exec -it mongo-mongos $MONGOSH_TLS_ADMIN --port 27017 --eval "$EVAL_APP_VARIABLES" --file /init/09-audit-profiling.js

echo -e "${BLUE}=== [6/6] Contrôle de l'état de l'infrastructure unifiée ===${NC}"
docker exec -it mongo-mongos $MONGOSH_TLS_ADMIN --port 27017 --eval 'sh.status()'

echo -e "${GREEN}=== [SUCCÈS] Architecture MongoDB Shardée et Sécurisée opérationnelle à 100% ! ===${NC}"
echo -e "${YELLOW}Toutes les briques logicielles (Personne A + Personne B) sont synchronisées.${NC}"