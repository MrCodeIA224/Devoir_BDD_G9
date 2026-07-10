// =============================================================================
// Initialise le replica set des config servers (csrs).
// À exécuter UNE FOIS, connecté sur configServ1, AVANT toute création d'utilisateur
// (on profite ici de la "localhost exception" : mongod autorise des
// opérations d'admin sans authentification tant qu'aucun utilisateur
// n'existe encore dans le cluster - la connexion doit néanmoins être en TLS
// puisque net.tls.mode=requireTLS s'applique indépendamment de l'auth).
// =============================================================================

rs.initiate({
  _id: "configReplSet",
  configsvr: true,
  members: [
    { _id: 0, host: "configServ1:27019" },
    { _id: 1, host: "configServ2:27019" },
    { _id: 2, host: "configServ3:27019" },
  ],
});

print("Attente de l'élection d'un PRIMARY sur le Replica Set de configuration...");
while (!rs.isMaster().ismaster) {
  sleep(1000);
}
print("[OK] csrs opérationnel, PRIMARY élu.");
