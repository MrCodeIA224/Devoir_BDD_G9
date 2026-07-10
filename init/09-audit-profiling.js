// =============================================================================
// Active le profiler MongoDB sur la base applicative pour tracer les accès
// (lecture ET écriture) aux collections cliniques. Comme l'authentification
// est active, chaque entrée de system.profile contient le champ "user",
// donnant une traçabilité nominative des accès — répond directement au
// besoin "logs d'accès aux dossiers de santé" du use case.
//
// Variables injectées via --eval : ROOT_USER, ROOT_PASSWORD, APP_DB_NAME
// =============================================================================

db.getSiblingDB("admin").auth(ROOT_USER, ROOT_PASSWORD);
const appDb = db.getSiblingDB(APP_DB_NAME);

// mode 1 = ne journalise que les opérations "lentes" (slowms) ; on force
// slowms à 0 pour journaliser TOUTES les opérations de lecture/écriture,
// nécessaire ici pour un objectif d'audit et non de perf-tuning seul.
appDb.setProfilingLevel(1, { slowms: 0 });

print("[OK] Profiler d'audit activé sur " + APP_DB_NAME + " (niveau 1, slowms=0).");
printjson(appDb.getProfilingStatus());
