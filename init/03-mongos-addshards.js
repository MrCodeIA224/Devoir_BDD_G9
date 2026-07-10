// =============================================================================
// Enregistre les 4 shards auprès du routeur mongos (exécuté sur ton mongos).
// Aligné sur les noms de conteneurs et de Replica Sets choisis par la Personne A.
// =============================================================================

const shards = [
  { rs: "shard1ReplSet", host: "shard1:27018" },
  { rs: "shard2ReplSet", host: "shard2:27018" },
  { rs: "shard3ReplSet", host: "shard3:27018" },
  { rs: "shard4ReplSet", host: "shard4:27018" },
];

shards.forEach((s) => {
  const res = sh.addShard(s.rs + "/" + s.host);
  printjson(res);
});

print("[OK] Les 4 shards configurés par la Personne A ont été enregistrés avec succès.");
printjson(sh.status());
