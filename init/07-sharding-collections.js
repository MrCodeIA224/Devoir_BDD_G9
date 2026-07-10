// =============================================================================
// Active le sharding sur la base applicative et shard la collection principale.
// Aligné sur le champ 'patient_id' choisi pour l'étude comparative (Partie 4).
//
// Variables injectées via --eval : ROOT_USER, ROOT_PASSWORD, APP_DB_NAME
// =============================================================================

db.getSiblingDB("admin").auth(ROOT_USER, ROOT_PASSWORD);

// 1. Activation du sharding à l'échelle de la base de données applicative
sh.enableSharding(APP_DB_NAME);

// 2. Sharding de la collection dossiers_patients (Index haché uniforme)
db.getSiblingDB(APP_DB_NAME).dossiers_patients.createIndex({ patient_id: "hashed" });
sh.shardCollection(APP_DB_NAME + ".dossiers_patients", { patient_id: "hashed" });

// 3. Sharding de la collection resultats_labo (Index haché uniforme)
db.getSiblingDB(APP_DB_NAME).resultats_labo.createIndex({ patient_id: "hashed" });
sh.shardCollection(APP_DB_NAME + ".resultats_labo", { patient_id: "hashed" });

print("[OK] Sharding activé sur " + APP_DB_NAME + " (clé hachée patient_id harmonisée).");
printjson(sh.status());