# 📑 CONTRIBUTION AU RAPPORT FINAL — Rôle de la Personne A : Infrastructure & Sharding

## 1. Description de l'Architecture Physique & Topologie du Cluster

Pour supporter la charge critique d'une plateforme nationale de centralisation de logs médicaux (Dossier Patient Partagé) tout en respectant les exigences strictes de la norme HDS (Hébergement des Données de Santé), nous avons conçu une infrastructure distribuée haute disponibilité sous **MongoDB 8.0**, orchestrée par **10 conteneurs Docker**. 

L'architecture est structurée de manière linéaire et transparente autour de trois composants majeurs :

*   **3 Serveurs de Configuration (Config Servers - `configServ1` à `configServ3`)** : Ils forment un Replica Set hautement disponible nommé `configReplSet` (port `27019`). Ils agissent comme le « cerveau » du cluster en stockant les métadonnées et la table de routage géographique des dossiers médicaux. L'usage de 3 nœuds (nombre impair) garantit le maintien du quorum (vote à la majorité) en cas de panne de l'un d'eux.
*   **4 Équipes de Fragments (Shards - `shard1` à `shard4`)** : Chargés du stockage physique des logs, ils répondent à l'obligation de scalabilité horizontale de l'énoncé. Depuis MongoDB 8.0, un shard ne peut plus être une instance isolée ; il doit obligatoirement être déclaré comme un Replica Set. 
    *   *Arbitrage technique clé (Banc d'essai)* : Afin de concilier contraintes matérielles (RAM de la machine de test) et rigueur académique, les shards 2, 3 et 4 ont été configurés en Replica Sets mono-nœud. À l'inverse, **le `shard1` a été étendu en un véritable Replica Set de 3 membres (`shard1`, `shard1-node2`, `shard1-node3`) sur le port `27018`**. Ce choix stratégique fournit un environnement réel pour démontrer les mécanismes de cohérence forte (`w: "majority"`) et tester la tolérance aux pannes en coupant des nœuds.
*   **1 Routeur Intelligent (Mongos - `mongos`)** : Exposé sur le port externe `27020`, il sert de point d'entrée unique et transparent pour les clients et l'application. Il interroge les Config Servers pour acheminer chaque requête vers le bon fragment sans que l'utilisateur n'ait à connaître la distribution physique des données.

---

## 2. Déploiement et Automatisation de l'Infrastructure

L'intégralité du cycle de vie du cluster a été automatisée à travers un orchestrateur Bash unifié (`init.sh`) exécuté sous **Ubuntu 26**, garantissant la reproductibilité parfaite de l'environnement pour toute l'équipe. Le processus suit un ordonnancement strict :

1.  **Gestion rigoureuse des permissions Linux** : Création manuelle de l'arborescence locale `./data/` et application d'un `chmod -R 777`. Cette étape est vitale : l'image Docker officielle de MongoDB effectue un basculement d'utilisateur de `root` vers `mongodb` (UID 999). Prévu en amont, ce mécanisme évite tout crash pour accès refusé (*Permission Denied*).
2.  **Sécurisation par Keyfile & Certificats** : Intégration de la directive `--keyFile` (droits `400`) pour verrouiller la communication inter-nœuds, et initialisation du chiffrement TLS obligatoire (`--tlsMode requireTLS`) via les certificats générés automatiquement par le script OpenSSL (`generate-certs.sh`).
3.  **Bootstrap et Élection logique** : Lancement des conteneurs en tâche de fond (`docker compose up -d`). Le script injecte ensuite séquentiellement les configurations logiques : élection du maître des Config Servers via `rs.initiate()`, initialisation des 4 Replica Sets de shards, puis rattachement de ces derniers au routeur central à l'aide de la commande administrative 
`sh.addShard()`.

---

## 3. Étude Comparative et Choix de la Clé de Sharding (Partie 4)

Afin d'assurer la viabilité du stockage des 50 000 dossiers médicaux injectés, trois stratégies de fragmentation ont été analysées pour le rapport :

1.  **Hashed Sharding sur `{ patient_id: "hashed" }` (Solution Retenue)** :
    *   *Mécanisme* : MongoDB applique une fonction de hachage MD5 sur l'identifiant unique du patient avant de déterminer son fragment de destination.
    *   *Justification* : Cette stratégie offre une distribution parfaitement équitable de la charge (vérifiée graphiquement via `sh.status()` avec **environ 25% de documents sur chacun des 4 shards**). Elle élimine définitivement les points chauds (*hotspots*) lors des phases d'écritures massives simultanées provenant de différents hôpitaux.
2.  **Ranged Sharding sur `{ date_creation: 1 }` (Rejetée)** :
    *   *Mécanisme* : Répartition linéaire par plages de valeurs chronologiques.
    *   *Raison du rejet* : Les logs médicaux arrivant en temps réel, 100% des nouvelles écritures s'empileraient sur le même shard à un instant T (le dernier de la plage), laissant les 3 autres inactifs. Ce goulot d'étranglement brise l'intérêt du sharding.
3.  **Compound Sharding sur `{ patient_id: 1, date_creation: 1 }` (Alternative recommandée en production)** :
    *   *Mécanisme* : Clé composite combinant l'ID du patient et le temps.
    *   *Analyse* : Idéale pour maximiser les performances de lecture ciblée (recherche de l'historique récent d'un patient par la Personne C), mais légèrement moins homogène sur l'équilibrage strict à l'écriture immédiate que la clé hachée.
