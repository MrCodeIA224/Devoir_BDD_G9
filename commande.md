# Commandes utiles — Démo Sharding & Sécurité (MongoDB 8.0)

Toutes les commandes sont prévues pour être copiées-collées telles quelles
depuis un terminal sur la machine hôte (pas besoin d'être déjà dans un
conteneur). Elles utilisent `docker exec` pour lancer `mongosh` à l'intérieur
des conteneurs, avec les certificats déjà présents dans chaque image.

> **Si le terminal semble bloqué après un collage** (l'invite affiche `>` au
> lieu de revenir à la ligne normale) : c'est que le copier-coller a coupé la
> commande au milieu d'une chaîne entre guillemets. Tape `'` puis `Entrée`
> pour fermer proprement, ou `Ctrl+C` pour tout annuler et recommence.
> Les commandes ci-dessous sont volontairement découpées sur plusieurs lignes
> avec des `\` pour éviter ce problème — copie bien le bloc en entier.

## 0. Rappel des identifiants

| Rôle                     | Utilisateur          | Mot de passe                  | DB d'authentification |
|--------------------------|----------------------|--------------------------------|------------------------|
| Root cluster             | `admin_root`         | `SuperSecretRootPassword2026`  | `admin`                |
| DBA infra (pas de data)  | `admin_infra_dba`    | `SecureDBAPassword2026`        | `admin`                |
| Médecin                  | `dr_diop`             | `MedecinPassword2026`          | `hopital_db`           |
| Infirmier                | `inf_mbacke`          | `InfirmierPassword2026`        | `hopital_db`           |
| Laborantin               | `lab_ndiaye`          | `LaborantinPassword2026`       | `hopital_db`           |
| Admin fonctionnel hôpital| `admin_fonctionnel`   | `AdminHopitalPassword2026`     | `hopital_db`           |
| Auditeur sécurité (SCRAM)| `auditeur_scram`      | `AuditeurPassword2026`         | `audit_db`             |
| App watcher (change streams) | `audit_watcher_app` | `WatcherAppPassword2026`     | `audit_db`             |
| Auditeur (x.509)         | certificat `client-auditeur.pem` | *(pas de mot de passe)* | `$external`      |

Base applicative : `hopital_db` — collections shardées : `dossiers_patients`,
`resultats_labo` (clé de shard `patient_id` en mode **hashed**).

---

## 1. Se connecter en administrateur (accès complet)

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u admin_root \
  -p 'SuperSecretRootPassword2026' \
  --authenticationDatabase admin
```

Tu obtiens un shell interactif. Toutes les commandes des sections 2 à 4
peuvent être tapées directement dedans, ou lancées en une ligne avec
`--eval '...'` comme montré ci-dessous (pratique pour la démo, pas besoin de
rester dans le shell).

---

## 2. Vérifier l'état global du sharding

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u admin_root \
  -p 'SuperSecretRootPassword2026' \
  --authenticationDatabase admin \
  --eval 'sh.status()'
```

Liste des shards et de leur santé :

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u admin_root \
  -p 'SuperSecretRootPassword2026' \
  --authenticationDatabase admin \
  --eval 'printjson(db.adminCommand({ listShards: 1 }))'
```

État du balancer (répartition automatique des chunks) :

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u admin_root \
  -p 'SuperSecretRootPassword2026' \
  --authenticationDatabase admin \
  --eval 'printjson(sh.getBalancerState()); printjson(sh.balancerCollectionStatus("hopital_db.dossiers_patients"))'
```

---

## 3. Voir la répartition des données via la clé hashée

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u admin_root \
  -p 'SuperSecretRootPassword2026' \
  --authenticationDatabase admin \
  --eval '
    db = db.getSiblingDB("hopital_db");
    print("--- Répartition dossiers_patients ---");
    db.dossiers_patients.getShardDistribution();
    print("--- Répartition resultats_labo ---");
    db.resultats_labo.getShardDistribution();
  '
```

`getShardDistribution()` affiche, par shard : nombre de chunks, nombre de
documents et taille — c'est la preuve visuelle que `patient_id` (hashed)
répartit bien les données sur les 4 shards.

**Comptage rapide (estimation, sans scan complet)** — utile si le volume est
important :

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u admin_root \
  -p 'SuperSecretRootPassword2026' \
  --authenticationDatabase admin \
  --eval '
    db = db.getSiblingDB("hopital_db");
    print("dossiers_patients:", db.dossiers_patients.estimatedDocumentCount());
    print("resultats_labo:", db.resultats_labo.estimatedDocumentCount());
  '
```

**Vérification physique directe** (taille réelle sur disque par shard,
simple et parlant en démo) :

```bash
for SHARD in mongo-shard1 mongo-shard2 mongo-shard3 mongo-shard4; do
  echo "=== $SHARD ==="
  docker exec "$SHARD" du -sh /data/db
done
```

---

## 4. (Optionnel) Injecter des données de test pour une démo plus parlante

Si `hopital_db` est vide, la répartition ci-dessus n'a rien à montrer.
Cette commande insère 300 faux dossiers patients puis réaffiche la
répartition :

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u admin_root \
  -p 'SuperSecretRootPassword2026' \
  --authenticationDatabase admin \
  --eval '
    db = db.getSiblingDB("hopital_db");
    let docs = [];
    for (let i = 0; i < 300; i++) {
      docs.push({ patient_id: i, nom: "Patient_" + i, diagnostic: "démo sharding", date: new Date() });
    }
    db.dossiers_patients.insertMany(docs);
    print(docs.length + " documents insérés dans dossiers_patients.");
    db.dossiers_patients.getShardDistribution();
  '
```

Pour un jeu de données plus complet et déjà aligné sur le schéma du projet
(dossiers_patients / resultats_labo / suivi_soins / access_logs), voir plutôt
`generate_dataset.py --insert-mongo` à la racine du projet.

---

## 5. Tester les accès par profil métier (RBAC)

Chaque bloc se connecte avec un compte différent et tente une opération
autorisée puis une opération qui **doit être refusée** (le refus prouve que
le RBAC fonctionne).

### 5.1 Médecin (`dr_diop`) — lecture/écriture, pas de suppression

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u dr_diop \
  -p 'MedecinPassword2026' \
  --authenticationDatabase hopital_db \
  --eval '
    db = db.getSiblingDB("hopital_db");
    print("Lecture dossiers_patients (doit réussir) :");
    printjson(db.dossiers_patients.findOne());
    print("Tentative de suppression (doit échouer) :");
    try { db.dossiers_patients.deleteOne({}); print("PROBLÈME : la suppression a été acceptée !"); }
    catch (e) { print("Refusé comme attendu -> " + e); }
  '
```

### 5.2 Infirmier (`inf_mbacke`) — bloqué sur la collection brute, OK sur la vue masquée

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u inf_mbacke \
  -p 'InfirmierPassword2026' \
  --authenticationDatabase hopital_db \
  --eval '
    db = db.getSiblingDB("hopital_db");
    print("Tentative lecture directe dossiers_patients (doit échouer) :");
    try { printjson(db.dossiers_patients.findOne()); print("PROBLÈME : accès direct autorisé !"); }
    catch (e) { print("Refusé comme attendu -> " + e); }
    print("Lecture via la vue de masquage v_dossiers_patients_infirmier (doit réussir) :");
    printjson(db.v_dossiers_patients_infirmier.findOne());
  '
```

### 5.3 Laborantin (`lab_ndiaye`) — uniquement les résultats de labo

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u lab_ndiaye \
  -p 'LaborantinPassword2026' \
  --authenticationDatabase hopital_db \
  --eval '
    db = db.getSiblingDB("hopital_db");
    print("Lecture resultats_labo (doit réussir) :");
    printjson(db.resultats_labo.findOne());
    print("Tentative lecture dossiers_patients (doit échouer) :");
    try { printjson(db.dossiers_patients.findOne()); print("PROBLÈME : accès autorisé !"); }
    catch (e) { print("Refusé comme attendu -> " + e); }
  '
```

### 5.4 Admin fonctionnel hôpital (`admin_fonctionnel`) — gestion des comptes locaux

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u admin_fonctionnel \
  -p 'AdminHopitalPassword2026' \
  --authenticationDatabase hopital_db \
  --eval '
    db = db.getSiblingDB("hopital_db");
    print("Liste des utilisateurs de hopital_db (doit réussir) :");
    printjson(db.getUsers());
    print("Tentative accès à audit_db.access_logs (doit échouer) :");
    try { printjson(db.getSiblingDB("audit_db").access_logs.findOne()); print("PROBLÈME : accès autorisé !"); }
    catch (e) { print("Refusé comme attendu -> " + e); }
  '
```

### 5.5 Auditeur sécurité — SCRAM classique (`auditeur_scram`)

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u auditeur_scram \
  -p 'AuditeurPassword2026' \
  --authenticationDatabase audit_db \
  --eval '
    db = db.getSiblingDB("audit_db");
    print("Lecture access_logs (doit réussir) :");
    printjson(db.access_logs.find().limit(5).toArray());
    db = db.getSiblingDB("hopital_db");
    print("Tentative lecture dossiers_patients (doit échouer) :");
    try { printjson(db.dossiers_patients.findOne()); print("PROBLÈME : accès autorisé !"); }
    catch (e) { print("Refusé comme attendu -> " + e); }
  '
```

---

## 6. Vérifier le profiler d'audit (traçabilité légale)

Le profiler est activé **par shard** (mongos ne le permet pas). On se
connecte donc directement à chaque shard pour lire ses dernières opérations
tracées :

```bash
for SHARD in mongo-shard1 mongo-shard2 mongo-shard3 mongo-shard4; do
  echo "=== $SHARD ==="
  docker exec -it "$SHARD" mongosh \
    --tls \
    --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
    --tlsCAFile /etc/mongo-certs/ca.pem \
    --port 27018 \
    -u admin_root \
    -p 'SuperSecretRootPassword2026' \
    --authenticationDatabase admin \
    --eval '
      db = db.getSiblingDB("hopital_db");
      printjson(db.getProfilingStatus());
      print("Dernières opérations tracées :");
      db.system.profile.find().sort({ ts: -1 }).limit(3).forEach(printjson);
    '
done
```

Chaque entrée `system.profile` contient le champ `user` (auth active) —
c'est la preuve de traçabilité nominative demandée par le use case.

---

## 7. (Bonus) Authentification par certificat x.509

Le certificat client de l'auditeur (`client-auditeur.pem`) n'est pas monté
dans le conteneur par défaut : on le copie temporairement avec `docker cp`,
puis on s'authentifie par certificat plutôt que par mot de passe.

```bash
docker cp certs/client-auditeur.pem mongo-mongos:/tmp/client-auditeur.pem
```

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /tmp/client-auditeur.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  --authenticationMechanism MONGODB-X509 \
  --authenticationDatabase '$external' \
  --eval '
    print("Connecté en tant que : " + db.runCommand({ connectionStatus: 1 }).authInfo.authenticatedUsers[0].user);
    db = db.getSiblingDB("audit_db");
    printjson(db.access_logs.find().limit(3).toArray());
  '
```

```bash
# Nettoyage du certificat temporaire dans le conteneur
docker exec -it mongo-mongos rm -f /tmp/client-auditeur.pem
```

---

## 8. Se reconnecter en admin à tout moment

```bash
docker exec -it mongo-mongos mongosh \
  --tls \
  --tlsCertificateKeyFile /etc/mongo-certs/node.pem \
  --tlsCAFile /etc/mongo-certs/ca.pem \
  --port 27017 \
  -u admin_root \
  -p 'SuperSecretRootPassword2026' \
  --authenticationDatabase admin
```
