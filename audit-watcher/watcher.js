/**
 * audit-watcher (Version harmonisée pour l'infrastructure unifiée)
 * -----------------------------------------------------------------------
 * Écoute les Change Streams des collections cliniques sensibles et écrit
 * une entrée d'audit structurée et chaînée (hash de l'entrée précédente)
 * dans audit_db.access_logs.
 * 
 * Valeurs par défaut alignées sur la base de données de la Personne A.
 */

const { MongoClient } = require("mongodb");
const crypto = require("crypto");

const {
  MONGO_URI,
  MONGO_APP_USER,
  MONGO_APP_PASSWORD,
  APP_DB_NAME = "hopital_db", // CORRIGÉ : aligné sur 'hopital_db'
} = process.env;

if (!MONGO_URI || !MONGO_APP_USER || !MONGO_APP_PASSWORD) {
  console.error("[FATAL] MONGO_URI, MONGO_APP_USER, MONGO_APP_PASSWORD sont requis.");
  process.exit(1);
}

const WATCHED_COLLECTIONS = ["dossiers_patients", "resultats_labo"];

function hashEntry(entry, previousHash) {
  const payload = JSON.stringify({ ...entry, previousHash });
  return crypto.createHash("sha256").update(payload).digest("hex");
}

async function main() {
  const client = new MongoClient(MONGO_URI, {
    auth: { username: MONGO_APP_USER, password: MONGO_APP_PASSWORD },
    authSource: "audit_db",
    tls: true,
    tlsCAFile: "/etc/mongo-certs/ca.pem", // Doit correspondre au montage de ton Compose
  });

  await client.connect();
  console.log("[OK] audit-watcher connecté au cluster sécurisé MongoDB.");

  const auditColl = client.db("audit_db").collection("access_logs");
  const appDb = client.db(APP_DB_NAME);

  // Récupère le hash de la dernière entrée pour poursuivre la chaîne après un redémarrage
  let previousHash = "GENESIS";
  const lastEntry = await auditColl.find().sort({ _id: -1 }).limit(1).next();
  if (lastEntry && lastEntry.entryHash) {
    previousHash = lastEntry.entryHash;
  }

  for (const collName of WATCHED_COLLECTIONS) {
    const changeStream = appDb.collection(collName).watch([], {
      fullDocument: "updateLookup",
    });

    changeStream.on("change", async (change) => {
      try {
        const entry = {
          ts: new Date(),
          collection: collName,
          operationType: change.operationType,
          documentKey: change.documentKey,
        };
        const entryHash = hashEntry(entry, previousHash);
        await auditColl.insertOne({ ...entry, previousHash, entryHash });
        previousHash = entryHash;
        console.log(
          `[AUDIT] ${entry.ts.toISOString()} ${entry.operationType} sur ${collName} ` +
            `doc=${JSON.stringify(entry.documentKey)}`
        );
      } catch (err) {
        console.error("[ERREUR] Échec d'écriture du log d'audit :", err);
      }
    });

    changeStream.on("error", (err) => {
      console.error(`[ERREUR] Change stream sur ${collName} interrompu :`, err);
    });

    console.log(`[OK] Surveillance active sur ${APP_DB_NAME}.${collName}`);
  }
}

main().catch((err) => {
  console.error("[FATAL]", err);
  process.exit(1);
});
