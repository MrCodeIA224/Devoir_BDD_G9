# 🛠️ Bilan Technique – Personne A : Infrastructure & Sharding

## Objectif

L'objectif de cette partie du projet était de **concevoir, déployer et documenter une infrastructure MongoDB 8.0 distribuée et hautement disponible**, capable de supporter la charge d'une plateforme nationale de gestion des logs médicaux.

Cette mission comprenait :

- la préparation de l'environnement Linux ;
- le déploiement de l'architecture distribuée avec Docker ;
- l'automatisation de l'initialisation du cluster ;
- la validation du fonctionnement du Sharding ;
- l'étude comparative des différentes stratégies de fragmentation des données.

---

# Étape 1 : Préparation de l'environnement Linux et gestion des permissions

## Objectif

Avant le lancement des conteneurs Docker, il est nécessaire de préparer l'arborescence qui accueillera les données persistantes de MongoDB.

### Commandes utilisées

```bash
# Création des répertoires destinés à stocker les données
# des Config Servers ainsi que des quatre Shards.
mkdir -p data/config1 data/config2 data/config3 data/shard1 data/shard2 data/shard3 data/shard4

mkdir -p data/shard1-node2 data/shard1-node3

# Attribution des permissions complètes afin que
# l'utilisateur MongoDB présent dans les conteneurs
# puisse accéder aux volumes sans erreur "Permission Denied".
chmod -R 777 data/
```

## Justification

MongoDB s'exécute dans les conteneurs Docker sous un utilisateur différent de **root**.

Si Docker crée automatiquement les dossiers, ceux-ci appartiennent généralement à **root**, ce qui empêche MongoDB d'écrire dans les volumes et provoque un arrêt immédiat du serveur.

La création manuelle des dossiers accompagnée des permissions garantit la persistance des données et évite tout conflit de droits d'accès.

---

# Étape 2 : Définition de l'architecture distribuée

## Architecture déployée

L'infrastructure est composée de huit conteneurs Docker :

- **3 Config Servers**
- **4 Shards**
- **1 Routeur Mongos**

Tous les conteneurs communiquent à travers un réseau Docker privé nommé **mongo-cluster**.

## Commande utilisée

```bash
# Démarrage de tous les conteneurs définis
# dans le fichier docker-compose.yml.
docker compose up -d

# Pause de 10 secondes afin de laisser
# MongoDB terminer complètement son démarrage.
sleep 10
```

## Justification

Les trois Config Servers assurent la **haute disponibilité** des métadonnées du cluster.

Depuis MongoDB 8.0, un shard ne peut plus être déclaré comme un simple serveur autonome.

Chaque shard doit obligatoirement appartenir à un **Replica Set**.

Afin de limiter la consommation de ressources, chaque Replica Set est constitué d'un seul membre, ce qui permet de reproduire fidèlement une architecture de production tout en restant léger.

---

# Étape 3 : Automatisation de l'initialisation du cluster

Afin d'éviter toute configuration manuelle, un script Bash nommé **init.sh** automatise entièrement la création du cluster.

---

## Initialisation des Config Servers

```bash
# Exécution de mongosh à l'intérieur du premier Config Server
# afin de créer le Replica Set "configReplSet".
docker exec -it mongo-config1 mongosh --port 27019 --eval '
rs.initiate({
    _id:"configReplSet",
    configsvr:true,
    members:[
        {_id:0,host:"configServ1:27019"},
        {_id:1,host:"configServ2:27019"},
        {_id:2,host:"configServ3:27019"}
    ]
})
'
```

### Justification

Cette commande :

- crée le Replica Set des Config Servers ;
- élit automatiquement un serveur primaire ;
- permet le stockage distribué des métadonnées du cluster.

Une pause est ensuite effectuée afin de laisser le temps à l'élection du nœud primaire.

```bash
# Attente de quelques secondes afin que
# l'élection du Primary soit terminée.
sleep 3
```

---

## Initialisation des quatre Shards

### Shard 1

```bash
# Création du Replica Set associé au premier shard.
docker exec -it mongo-shard1 mongosh --port 27018 --eval \
'rs.initiate({_id: "shard1ReplSet", members: [{_id: 0, host: "shard1:27018"}, {_id: 1, host: "shard1-node2:27018"}, {_id: 2, host: "shard1-node3:27018"}]})'
```

### Shard 2

```bash
# Création du Replica Set associé au deuxième shard.
docker exec -it mongo-shard2 mongosh --port 27018 --eval \
'rs.initiate({_id:"shard2ReplSet",members:[{_id:0,host:"shard2:27018"}]})'
```

### Shard 3

```bash
# Création du Replica Set associé au troisième shard.
docker exec -it mongo-shard3 mongosh --port 27018 --eval \
'rs.initiate({_id:"shard3ReplSet",members:[{_id:0,host:"shard3:27018"}]})'
```

### Shard 4

```bash
# Création du Replica Set associé au quatrième shard.
docker exec -it mongo-shard4 mongosh --port 27018 --eval \
'rs.initiate({_id:"shard4ReplSet",members:[{_id:0,host:"shard4:27018"}]})'
```

Après l'initialisation des quatre Replica Sets, une nouvelle pause est réalisée.

```bash
# Attente de la finalisation des Replica Sets
# avant leur rattachement au cluster.
sleep 3
```

## Justification

Même si chaque Replica Set ne possède qu'un seul membre, MongoDB exige désormais cette configuration avant d'autoriser l'ajout d'un shard au cluster.

---

# Étape 4 : Rattachement des Shards au Routeur Mongos

Une fois les Replica Sets créés, ceux-ci doivent être enregistrés auprès du routeur **mongos**.

```bash
# Connexion au routeur Mongos afin d'ajouter
# chacun des quatre Replica Sets comme shard.
docker exec -it mongo-mongos mongosh --port 27017 --eval '
sh.addShard("shard1ReplSet/shard1:27018");
sh.addShard("shard2ReplSet/shard2:27018");
sh.addShard("shard3ReplSet/shard3:27018");
sh.addShard("shard4ReplSet/shard4:27018");
'
```

## Justification

Les commandes `sh.addShard()` enregistrent chaque Replica Set auprès du routeur central.

À partir de cet instant, MongoDB peut distribuer automatiquement les collections entre les différents shards.

Une courte pause est ensuite réalisée.

```bash
# Attente de la prise en compte des nouveaux shards
# par le routeur Mongos.
sleep 2
```

---

# Étape 5 : Vérification de la topologie du cluster

Une fois l'infrastructure entièrement configurée, il est nécessaire de vérifier son état.

```bash
# Affichage de la configuration complète du cluster :
# Replica Sets, Balancer, Shards et état général.
docker exec -it mongo-mongos mongosh --port 27017 --eval 'sh.status()'
```

## Résultat obtenu

La commande retourne notamment :

- `ok : 1`
- les quatre Replica Sets correctement enregistrés ;
- le Balancer actif ;
- le routeur Mongos fonctionnel ;
- la version MongoDB 8.0.

Cette sortie confirme que l'architecture distribuée est totalement opérationnelle.

---

# Étape 6 : Étude comparative des stratégies de Sharding

Trois stratégies ont été étudiées afin de déterminer la meilleure méthode de distribution des logs médicaux.

## 1. Hashed Sharding (Solution retenue)

```javascript
{ patient_id : "hashed" }
```

### Principe

MongoDB calcule une valeur de hachage du champ `patient_id` avant de répartir les documents.

### Avantages

- excellente répartition de la charge ;
- environ 25 % des données sur chacun des quatre shards ;
- suppression des points chauds ;
- performances constantes lors des écritures massives.

### Pourquoi ce choix ?

Les logs médicaux sont générés simultanément par plusieurs établissements de santé.

Le hachage permet donc d'éviter qu'un seul shard reçoive toutes les écritures.

---

## 2. Ranged Sharding

```javascript
{ date_creation : 1 }
```

### Principe

Les documents sont répartis selon leur date de création.

### Inconvénient majeur

Les nouveaux logs arrivent en continu.

Toutes les nouvelles insertions seraient donc dirigées vers un unique shard.

Cela provoquerait :

- un hotspot ;
- un déséquilibre de charge ;
- une sous-utilisation des autres shards.

Cette solution a donc été rejetée.

---

## 3. Compound Sharding

```javascript
{ patient_id : 1, date_creation : 1 }
```

### Principe

La clé de fragmentation combine l'identifiant du patient et la date de création.

### Avantages

- recherches très rapides sur l'historique d'un patient ;
- excellente compatibilité avec les requêtes analytiques.

### Limites

La distribution reste légèrement moins homogène que celle obtenue avec une clé de hachage.

---

# Conclusion

L'ensemble de cette partie a permis de mettre en place une architecture MongoDB 8.0 distribuée reposant sur :

- une infrastructure Docker entièrement automatisée ;
- trois Config Servers assurant la haute disponibilité ;
- quatre Shards configurés en Replica Sets ;
- un routeur Mongos centralisant les accès ;
- une stratégie de Sharding par hachage garantissant une excellente répartition de la charge.

Cette infrastructure constitue une base robuste et évolutive pour l'exploitation d'une plateforme nationale de gestion des logs médicaux.