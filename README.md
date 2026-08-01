# 🏥 Plateforme Nationale de Centralisation de Logs Médicaux (Dossier Patient Partagé)
> **Master en Intelligence Artificielle (Dakar)**  
> *Livrable Commun d'Architecture NoSQL & Sécurité Avancée — MongoDB 8.0 & Docker v3.8*

Ce dépôt contient l'implémentation complète, industrialisée et hautement sécurisée d'un cluster MongoDB 8.0 distribué. Ce projet applique les concepts de **Sharding horizontal à 4 fragments** et de **sécurité multi-niveaux (TLS / RBAC / Audit / Data Masking)** à un cas d'usage critique : la centralisation nationale des comptes-rendus cliniques et de la traçabilité des accès aux dossiers de santé (HDS / RGPD).

---

## 📐 Architecture Réseau et Topologie du Cluster

Le cluster isole logiquement les flux réseau pour empêcher toute intrusion directe sur les nœuds de stockage :

---------------------

### 🔒 Cloisonnement des Réseaux Docker
*   **Zone Interne Étanche (`backend-net / internal: true`)** : Les fragments (*shards*) et les serveurs de métadonnées (*config servers*) y sont confinés. Ils ne publient aucun port vers l'extérieur et sont invisibles pour la machine hôte. Isolation réseau = première ligne de défense.
*   **Zone d'Entrée Privilégiée (`frontend-net`)** : Seul le routeur unique `mongos` (Port `27020:27017`) et le microservice d'infrastructure `audit-watcher` communiquent sur ce segment pour interagir avec l'extérieur.

---

## 🛠️ Matrice de Sécurité Implémentée (Partie 2)

| Domaine de Contrôle | Mécanisme Technique | Localisation Logicielle |
| :--- | :--- | :--- |
| **Authentification inter-nœuds** | Clé secrète partagée de 756 octets base64 | `keyfile/`, `docker-compose.yml` (`secrets`) |
| **Chiffrement en Transit** | TLS Mutuel obligatoire (`requireTLS` / TLS v1.3) | `certs/`, `config/*.conf` |
| **Authentification Client** | SCRAM-SHA-256 robuste | `init/04-create-admin-users.js` |
| **Double Facteur Authentification** | Certificat numérique client externe X.509 | `certs/generate-certs.sh`, `init/06-*.js` |
| **Contrôle d'Accès Applicatif** | Modèle RBAC sur-mesure (0% action `delete`) | `init/05-rbac-roles.js` |
| **Confidentialité des Champs** | Data Masking par projections de Vues dynamiques | `init/08-views-field-redaction.js` |
| **Chiffrement au Repos** | CSFLE applicatif (Chiffrement côté client) | `csfle/` |
| **Traçabilité des Consultations** | Profiler acquis (`slowms: 0`) + Change Streams | `init/09-audit-profiling.js`, `audit-watcher/` |
| **Durcissement des Conteneurs** | Cap_drop ALL, no-new-privileges, User non-root | `docker-compose.yml` |

---

## 📂 Organisation Commune du Code Source (VS Code structure)

```text
DEVOIR_BDD_G9/
├── audit-watcher/       --> Microservice Node.js de capture des écritures en temps réel (Change Streams)
├── certs/               --> Dossier contenant generate-certs.sh + l'ensemble des clés, .pem et .crt générés
├── config/              --> Fichiers de configuration .conf injectés dans les daemons mongod/mongos
├── csfle/               --> Module bonus de chiffrement côté client (Field-Level Encryption)
├── data/                --> Volumes locaux persistants de stockage des fragments et métadonnées
├── init/                --> Scripts JavaScript d'initialisation logique ordonnés (01 à 09)
├── keyfile/             --> Script generate-keyfile.sh + la clé générée mongo-cluster.key
├── .gitignore           --> Gestion des exclusions Git (masquage des fichiers binaires data/)
├── docker-compose.yml   --> Définition de l'infrastructure physique multi-nœuds (10 conteneurs)
├── generate_dataset.py  --> Script Python d'injection massive du jeu de données (50 000 entrées)
├── init.sh              --> Orchestrateur global de déploiement automatique du cluster en 1 clic
├── PARTIE_C_coherence_performances.md --> Espace de travail pour les benchmarks et la cohérence
├── README.md            --> Ce guide d'explication et de gouvernance du projet
├── teardown.sh          --> Arrêt des conteneurs en préservant l'état des bases
└── test-security.sh     --> Suite d'assertions d'audit affichant la validation PASS/FAIL des rôles
```

---

## 🚀 Guide de Prise en Main (Procédure d'Équipe)

Pour lancer l'environnement complet et synchronisé sur votre machine Ubuntu, exécutez ces commandes depuis la racine du projet :

### 1. Générer les secrets cryptographiques de sécurité
```bash
# A. Générer la clé d'authentification interne du cluster
cd keyfile/ && chmod +x generate-keyfile.sh && ./generate-keyfile.sh && cd ..

# B. Générer l'autorité de certification locale (CA) et les certificats TLS serveurs/clients
cd certs/ && chmod +x generate-certs.sh && sudo ./generate-certs.sh && cd ..
```

### 2. Déployer et initialiser l'ensemble du Cluster
```bash
chmod +x init.sh
./init.sh
```
*Le script crée les répertoires, applique les droits Unix (`777` sur les volumes / `400` sur la clé), démarre les conteneurs, applique les configurations d'infrastructure, crée les comptes privilèges, puis déploie l'intelligence RBAC, le masquage et l'audit (`01` à `09`).*

### 3. Valider la sécurité pour le rapport écrit
```bash
chmod +x test-security.sh
./test-security.sh
```
*Vérifie la robustesse du cluster face aux intrusions anonymes, sans TLS, aux violations de droits du laborantin/infirmier et valide la connexion x.509 de l'auditeur.*

### 4. Arrêt et nettoyage de l'espace
```bash
chmod +x teardown.sh
./teardown.sh        # Arrête les processus sans altérer vos données locales
docker compose down -v  # Utilisez cette variante uniquement pour vider les volumes et repartir de zéro
```

---

## 👥 Comptes Professionnels et Périmètres RBAC créés

| Identifiant Utilisateur | Rôle Personnalisé | Périmètre d'Action Fonctionnel |
| :--- | :--- | :--- |
| `admin_root` | `root` | Administrateur global du cluster (Fermeture de la Localhost Exception). |
| `admin_infra_dba` | `clusterAdmin` | Gestion de l'infrastructure matérielle. **0% accès aux données de santé**. |
| `dr_diop` | `role_medecin` | Lecture/Écriture complète sur `dossiers_patients`. **Suppression interdite**. |
| `inf_mbacke` | `role_infirmier` | **Lecture seule sur la vue masquée** `v_dossiers_patients_infirmier` + Écriture soins. |
| `lab_ndiaye` | `role_laborantin` | Accès exclusif à `resultats_labo`. **Cloisonnement total du dossier clinique**. |
| `admin_fonctionnel` | `role_admin_hopital` | Gestion des comptes locaux et indexation au sein de l'établissement. |
| `auditeur_scram` / `auditeur_secu_x509` | `role_auditeur_securite` | Lecture seule de `system.profile` et `access_logs`. Aucun accès aux données cliniques. |
| `audit_watcher_app` | `role_app_watcher` | Jeton applicatif interne utilisé par le conteneur Node.js pour capter les Change Streams. |

---

## 💡 Choix Méthodologiques, Limites Académiques & Pistes de Production

Pour assurer une transparence scientifique optimale lors de la soutenance devant le jury, nous assumons et documentons les arbitrages techniques suivants :

1.  **Architecture Asymétrique des Fragments (Partie 1 & 3)** : En production, 100% des shards doivent être redondants. Afin de préserver la RAM de notre machine de test, nous avons configuré les Shards 2, 3 et 4 en nœuds uniques. À l'inverse, nous avons étendu le **`shard1` en un véritable Replica Set de 3 membres** (`shard1`, `shard1-node2`, `shard1-node3`). Ce choix offre à la **Personne C** un banc d'essai réel pour valider les concepts de tolérance aux pannes et comparer les comportements entre `w:1` et `w:majority`.
2.  **Audit en Version Community (Partie 2 & 6)** : Le moteur d'audit natif filtrable de MongoDB est restreint aux éditions Enterprise/Atlas. Nous contournons cette limite en associant le profiler natif poussé à l'extrême (`slowms: 0`), interceptant l'intégralité des requêtes de lecture nominatives, à un microservice réactif (`audit-watcher`) qui scelle l'historique des écritures.
3.  **Intégrité et Cryptographie des Journaux d'Audit** : La persistance des logs dans `audit_db.access_logs` applique un algorithme de **chaînage de blocs cryptographiques par hash SHA-256** (chaque log inclut le hash de l'entrée précédente). Ce mécanisme applicatif garantit la détection immédiate de toute tentative de modification malveillante des traces d'accès.

---

## 🎯 Conclusion (Validation Finale du Rôle d'Infrastructure)

L'ensemble de cette partie a permis de mettre en place une architecture MongoDB 8.0 distribuée hautement sécurisée reposant sur :

*   Une infrastructure Docker entièrement automatisée et reproductible ;