// =============================================================================
// Crée le premier utilisateur (root) — cette opération DÉSACTIVE
// définitivement la "localhost exception". À partir d'ici, toute connexion,
// y compris locale, doit s'authentifier.
//
// Variables injectées via --eval :
//   ROOT_USER, ROOT_PASSWORD, DBA_USER, DBA_PASSWORD
// =============================================================================

if (typeof ROOT_USER === "undefined" || typeof ROOT_PASSWORD === "undefined") {
  throw new Error("ROOT_USER / ROOT_PASSWORD doivent être injectés via --eval.");
}

db.getSiblingDB("admin").createUser({
  user: ROOT_USER,
  pwd: ROOT_PASSWORD,
  roles: [{ role: "root", db: "admin" }],
});
print("[OK] Utilisateur root créé : " + ROOT_USER);

// À partir d'ici la localhost exception est fermée : les commandes
// suivantes de CE script s'exécutent encore dans la même session mongosh
// déjà "connectée", mais toute NOUVELLE session devra s'authentifier.

if (typeof DBA_USER !== "undefined" && typeof DBA_PASSWORD !== "undefined") {
  db.getSiblingDB("admin").auth(ROOT_USER, ROOT_PASSWORD);

  // Séparation des tâches : le DBA infrastructure gère le cluster
  // (shards, replica sets, backups) mais N'A PAS accès aux données
  // médicales — principe de moindre privilège / cloisonnement des rôles.
  db.getSiblingDB("admin").createUser({
    user: DBA_USER,
    pwd: DBA_PASSWORD,
    roles: [
      { role: "clusterAdmin", db: "admin" },
      { role: "clusterManager", db: "admin" },
      { role: "hostManager", db: "admin" },
      { role: "backup", db: "admin" },
      { role: "restore", db: "admin" },
    ],
  });
  print("[OK] Utilisateur DBA cluster créé (pas d'accès aux données) : " + DBA_USER);
}
