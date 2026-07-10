// =============================================================================
// Initialise le replica set d'un shard. Générique : SHARD_HOST et SHARD_RS
// doivent être injectés via --eval avant ce fichier, ex :
//   mongosh --eval 'var SHARD_HOST="shard01", SHARD_RS="shard01rs";' \
//           --tls --tlsCAFile ... 02-init-shard-rs.js
// (voir scripts/02-run-init.sh qui automatise cela pour les 4 shards)
// =============================================================================

if (typeof SHARD_HOST === "undefined" || typeof SHARD_RS === "undefined") {
  throw new Error("SHARD_HOST et SHARD_RS doivent être définis via --eval avant ce script.");
}

rs.initiate({
  _id: SHARD_RS,
  members: [{ _id: 0, host: SHARD_HOST + ":27018" }],
});

print("Attente de l'élection d'un PRIMARY sur " + SHARD_RS + "...");
while (!rs.isMaster().ismaster) {
  sleep(1000);
}
print("[OK] " + SHARD_RS + " opérationnel, PRIMARY élu.");

print("");
print("NOTE (Partie 1 - Sharding) : ce devoir se concentre sur la Partie 2");
print("(Sécurité). Chaque shard est ici un replica set MONO-NŒUD pour rester");
print("gérable en Docker Compose sur une seule machine. Pour une architecture");
print("de production/Partie 1, dupliquez le service de ce shard dans");
print("docker-compose.yml (3 membres : 2 data-bearing + 1 arbiter, ou 3");
print("data-bearing) et ajoutez-les ici dans members[].");
