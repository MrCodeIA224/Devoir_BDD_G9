#!/usr/bin/env bash
# =============================================================================
# Génère une Autorité de Certification (CA) locale auto-signée, puis un
# certificat serveur par nœud du cluster (config servers, shards, mongos),
# ainsi qu'un certificat client x.509 pour la démonstration d'authentification
# par certificat (compte auditeur sécurité).
#
# ATTENTION : CA auto-signée = usage pédagogique / dev uniquement.
# En production : PKI d'entreprise ou autorité type Let's Encrypt/Vault.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

DAYS_VALID=825
CA_SUBJ="/C=SN/ST=Dakar/L=Dakar/O=DIT-MasterIA/OU=NoSQL-Devoir/CN=DPP-Root-CA"

# Nœuds serveurs du cluster (le nom DOIT correspondre au nom du service
# docker-compose car c'est le hostname utilisé pour la résolution DNS interne)
SERVER_NODES=(
  "configServ1" "configServ2" "configServ3"
  "shard1" "shard1-node2" "shard1-node3" "shard2" "shard3" "shard4"
  "mongos"
)

echo "== 1/4 : Génération de la CA racine =="
if [ ! -f ca.key ]; then
  openssl genrsa -out ca.key 4096
  openssl req -x509 -new -nodes -key ca.key -sha256 -days "$DAYS_VALID" \
    -out ca.pem -subj "$CA_SUBJ"
  echo "[OK] CA générée : ca.pem"
else
  echo "[i] CA déjà présente, réutilisation."
fi

echo "== 2/4 : Génération des certificats serveur (1 par nœud) =="
for NODE in "${SERVER_NODES[@]}"; do
  echo " -> $NODE"

  cat > "${NODE}.cnf" <<CNF
[req]
default_bits       = 2048
prompt             = no
default_md         = sha256
distinguished_name = dn
req_extensions     = req_ext

[dn]
C  = SN
ST = Dakar
L  = Dakar
O  = DIT-MasterIA
OU = NoSQL-Devoir
CN = ${NODE}

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${NODE}
DNS.2 = localhost
DNS.3 = ${NODE}.mongo-security-net
IP.1  = 127.0.0.1
CNF

  openssl genrsa -out "${NODE}.key" 2048
  openssl req -new -key "${NODE}.key" -out "${NODE}.csr" -config "${NODE}.cnf"
  openssl x509 -req -in "${NODE}.csr" -CA ca.pem -CAkey ca.key -CAcreateserial \
    -out "${NODE}.crt" -days "$DAYS_VALID" -sha256 \
    -extensions req_ext -extfile "${NODE}.cnf"

  # MongoDB veut un seul fichier PEM contenant clé privée + certificat
  cat "${NODE}.key" "${NODE}.crt" > "${NODE}.pem"
  chmod 600 "${NODE}.pem"
  rm -f "${NODE}.csr" "${NODE}.cnf"
done

echo "== 3/4 : Génération du certificat client TLS générique (scripts d'administration) =="
ADMIN_CLIENT_SUBJ="/C=SN/ST=Dakar/L=Dakar/O=DIT-MasterIA/OU=NoSQL-Devoir/CN=admin-client"
openssl genrsa -out admin-client.key 2048
openssl req -new -key admin-client.key -out admin-client.csr -subj "$ADMIN_CLIENT_SUBJ"
openssl x509 -req -in admin-client.csr -CA ca.pem -CAkey ca.key -CAcreateserial \
  -out admin-client.crt -days "$DAYS_VALID" -sha256
cat admin-client.key admin-client.crt > admin-client.pem
chmod 600 admin-client.pem
rm -f admin-client.csr
echo "     (ce certificat sert uniquement à satisfaire le handshake TLS mutuel"
echo "      requis par net.tls.mode=requireTLS ; l'identité applicative reste"
echo "      déterminée par SCRAM-SHA-256 (utilisateur/mot de passe), sauf pour"
echo "      le compte auditeur qui démontre en plus l'auth x.509 dédiée.)"

echo "== 4/4 : Génération du certificat client x.509 (compte auditeur) =="
# OU différent de celui des certs serveur (NoSQL-Devoir) : un DN client
# identique à celui des membres du cluster est refusé par MongoDB lors de
# la création de l'utilisateur x.509 (voir init/06-create-app-users.js).
CLIENT_SUBJ="/C=SN/ST=Dakar/L=Dakar/O=DIT-MasterIA/OU=ClientsExternes/CN=auditeur_secu_x509"
openssl genrsa -out client-auditeur.key 2048
openssl req -new -key client-auditeur.key -out client-auditeur.csr -subj "$CLIENT_SUBJ"
openssl x509 -req -in client-auditeur.csr -CA ca.pem -CAkey ca.key -CAcreateserial \
  -out client-auditeur.crt -days "$DAYS_VALID" -sha256
cat client-auditeur.key client-auditeur.crt > client-auditeur.pem
chmod 600 client-auditeur.pem
rm -f client-auditeur.csr

echo ""
echo "== Alignement des permissions avec l'utilisateur 'mongodb' (uid 999) du conteneur =="
echo "   (nécessaire car les certs sont montés en bind-mount, sans remapping d'UID Docker)"
if chown 999:999 ./*.pem 2>/dev/null; then
  echo "[OK] Propriétaire des .pem mis à 999:999."
else
  echo "[!] Impossible de chown en 999:999 (droits insuffisants)."
  echo "    -> Relancez ce script avec 'sudo ./generate-certs.sh', OU"
  echo "    -> passez les .pem en mode 644 (moins strict : chmod 644 ./*.pem)"
  echo "       Un mode trop restrictif + mauvais propriétaire empêchera mongod"
  echo "       (qui tourne en uid 999 dans le conteneur) de lire son certificat."
fi
chmod 600 ./*.pem

echo ""
echo "[OK] Tous les certificats sont générés dans $(pwd)"
echo "     Le CN du certificat client (auditeur_secu_x509) doit être créé"
echo "     tel quel comme utilisateur \$external dans MongoDB (voir init/)."