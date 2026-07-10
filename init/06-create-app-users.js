// =============================================================================
// Crée les comptes utilisateurs métier, chacun lié à EXACTEMENT un rôle RBAC
// (principe du moindre privilège). Variables injectées via --eval :
//   ROOT_USER, ROOT_PASSWORD, APP_DB_NAME,
//   MEDECIN_USER, MEDECIN_PASSWORD,
//   INFIRMIER_USER, INFIRMIER_PASSWORD,
//   LABORANTIN_USER, LABORANTIN_PASSWORD,
//   ADMIN_HOPITAL_USER, ADMIN_HOPITAL_PASSWORD,
//   AUDITEUR_USER, AUDITEUR_PASSWORD,
//   APP_USER, APP_PASSWORD
// =============================================================================

db.getSiblingDB("admin").auth(ROOT_USER, ROOT_PASSWORD);

const appDb = db.getSiblingDB(APP_DB_NAME);

appDb.createUser({
  user: MEDECIN_USER,
  pwd: MEDECIN_PASSWORD,
  roles: [{ role: "role_medecin", db: APP_DB_NAME }],
});

appDb.createUser({
  user: INFIRMIER_USER,
  pwd: INFIRMIER_PASSWORD,
  roles: [{ role: "role_infirmier", db: APP_DB_NAME }],
});

appDb.createUser({
  user: LABORANTIN_USER,
  pwd: LABORANTIN_PASSWORD,
  roles: [{ role: "role_laborantin", db: APP_DB_NAME }],
});

appDb.createUser({
  user: ADMIN_HOPITAL_USER,
  pwd: ADMIN_HOPITAL_PASSWORD,
  roles: [{ role: "role_admin_hopital", db: APP_DB_NAME }],
});

// Compte applicatif utilisé par le service audit-watcher (change streams) :
// lecture seule sur les collections cliniques (pour détecter les
// changements) + écriture sur audit_db.access_logs uniquement.
const auditDb = db.getSiblingDB("audit_db");
auditDb.createRole({
  role: "role_app_watcher",
  privileges: [
    { resource: { db: APP_DB_NAME, collection: "dossiers_patients" }, actions: ["find", "changeStream"] },
    { resource: { db: APP_DB_NAME, collection: "resultats_labo" }, actions: ["find", "changeStream"] },
    { resource: { db: "audit_db", collection: "access_logs" }, actions: ["find", "insert"] },
  ],
  roles: [],
});
auditDb.createUser({
  user: APP_USER,
  pwd: APP_PASSWORD,
  roles: [{ role: "role_app_watcher", db: "audit_db" }],
});

// Compte auditeur sécurité (authentification SCRAM classique)
auditDb.createUser({
  user: AUDITEUR_USER,
  pwd: AUDITEUR_PASSWORD,
  roles: [{ role: "role_auditeur_securite", db: "audit_db" }],
});

print("[OK] Comptes métier créés : " + MEDECIN_USER + ", " + INFIRMIER_USER +
      ", " + LABORANTIN_USER + ", " + ADMIN_HOPITAL_USER + ", " + AUDITEUR_USER +
      ", " + APP_USER);

// -----------------------------------------------------------------------
// BONUS — authentification par certificat x.509 pour le même auditeur.
// Alignement de la chaîne DN selon l'ordre strict attendu par MongoDB 8.0 
// issu de la génération OpenSSL (C=SN, ST=Dakar, L=Dakar...).
// -----------------------------------------------------------------------
const CLIENT_CERT_SUBJECT = "C=SN,ST=Dakar,L=Dakar,O=DIT-MasterIA,OU=NoSQL-Devoir,CN=auditeur_secu_x509";

db.getSiblingDB("$external").createUser({
  user: CLIENT_CERT_SUBJECT,
  roles: [{ role: "role_auditeur_securite", db: "audit_db" }],
});

print("[OK] Utilisateur x.509 $external créé avec succès pour : " + CLIENT_CERT_SUBJECT);