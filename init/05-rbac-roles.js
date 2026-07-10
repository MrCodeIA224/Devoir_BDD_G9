// =============================================================================
// RBAC métier — Dossier Patient Partagé
// Rôles personnalisés (db.createRole) construits sur le principe du moindre
// privilège : chaque rôle ne reçoit QUE les actions strictement nécessaires
// à sa fonction, sur les ressources (collections) strictement nécessaires.
//
// Variables injectées via --eval : ROOT_USER, ROOT_PASSWORD, APP_DB_NAME
// =============================================================================

const authDb = db.getSiblingDB("admin");
authDb.auth(ROOT_USER, ROOT_PASSWORD);

const appDb = db.getSiblingDB(APP_DB_NAME);

// -----------------------------------------------------------------------
// 1) role_medecin — lecture/écriture sur les dossiers patients et les
//    résultats de labo de son établissement. Pas de suppression (intégrité
//    du dossier médical : on corrige/complète, on ne supprime pas
//    l'historique — traçabilité légale).
// -----------------------------------------------------------------------
appDb.createRole({
  role: "role_medecin",
  privileges: [
    {
      resource: { db: APP_DB_NAME, collection: "dossiers_patients" },
      actions: ["find", "insert", "update"],
    },
    {
      resource: { db: APP_DB_NAME, collection: "resultats_labo" },
      actions: ["find", "insert", "update"],
    },
  ],
  roles: [],
});

// -----------------------------------------------------------------------
// 2) role_infirmier — lecture SEULE, et uniquement via une vue qui masque
//    les champs cliniques les plus sensibles (voir init/08-views-*.js).
//    Écriture limitée aux constantes/soins courants (collection dédiée,
//    volontairement séparée du dossier médical complet).
// -----------------------------------------------------------------------
appDb.createRole({
  role: "role_infirmier",
  privileges: [
    {
      resource: { db: APP_DB_NAME, collection: "v_dossiers_patients_infirmier" },
      actions: ["find"],
    },
    {
      resource: { db: APP_DB_NAME, collection: "resultats_labo" },
      actions: ["find"],
    },
    {
      resource: { db: APP_DB_NAME, collection: "suivi_soins" },
      actions: ["find", "insert", "update"],
    },
  ],
  roles: [],
});

// -----------------------------------------------------------------------
// 3) role_laborantin — accès exclusif aux résultats de laboratoire.
//    AUCUN accès au dossier médical complet (diagnostics, antécédents) :
//    cloisonnement strict entre "qui produit la donnée labo" et
//    "qui interprète le dossier clinique complet".
// -----------------------------------------------------------------------
appDb.createRole({
  role: "role_laborantin",
  privileges: [
    {
      resource: { db: APP_DB_NAME, collection: "resultats_labo" },
      actions: ["find", "insert", "update"],
    },
  ],
  roles: [],
});

// -----------------------------------------------------------------------
// 4) role_admin_hopital — administration applicative locale (gestion des
//    comptes utilisateurs de SON établissement) mais PAS d'accès aux
//    journaux d'audit.
//    Correction : Syntaxe explicite de MongoDB pour appliquer les privilèges
//    sur toutes les collections de la base applicative sans générer d'erreur.
// -----------------------------------------------------------------------
appDb.createRole({
  role: "role_admin_hopital",
  privileges: [
    {
      // En mettant une chaîne vide pour la collection mais en ciblant la DB,
      // MongoDB l'applique aux privilèges de gestion de la DB elle-même (ex: listCollections)
      resource: { db: APP_DB_NAME, collection: "" },
      actions: ["createIndex", "listCollections"],
    },
    {
      // Pour autoriser find/insert/update sur TOUTES les collections de cette DB,
      // on utilise l'arborescence de privilèges correcte ou on liste les collections clés.
      resource: { db: APP_DB_NAME, collection: "dossiers_patients" },
      actions: ["find", "insert", "update"],
    },
    {
      resource: { db: APP_DB_NAME, collection: "resultats_labo" },
      actions: ["find", "insert", "update"],
    },
    {
      resource: { db: APP_DB_NAME, collection: "suivi_soins" },
      actions: ["find", "insert", "update"],
    },
  ],
  roles: [
    { role: "userAdmin", db: APP_DB_NAME },
  ],
});

// -----------------------------------------------------------------------
// 5) role_auditeur_securite — lecture SEULE des journaux d'audit /
//    profiling. Aucun accès (même en lecture) aux données cliniques.
// -----------------------------------------------------------------------
const auditDb = db.getSiblingDB("audit_db");
auditDb.createRole({
  role: "role_auditeur_securite",
  privileges: [
    {
      resource: { db: "audit_db", collection: "access_logs" },
      actions: ["find"],
    },
    {
      resource: { db: APP_DB_NAME, collection: "system.profile" },
      actions: ["find"],
    },
  ],
  roles: [],
});

print("[OK] Rôles métier RBAC créés et corrigés : role_medecin, role_infirmier, role_laborantin, role_admin_hopital, role_auditeur_securite");
