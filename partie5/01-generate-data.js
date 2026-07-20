// Partie 5 — Génération de données de test (100 000 patients)
// Exécution : via mongosh authentifié (compte admin)

const db5 = db.getSiblingDB("hopital_db");

const prenoms = ["Awa", "Moussa", "Fatou", "Ibrahima", "Aissatou", "Ousmane", "Mariama", "Cheikh", "Khady", "Mamadou"];
const noms = ["Diop", "Ndiaye", "Fall", "Sow", "Ba", "Diallo", "Faye", "Gueye", "Mbaye", "Sarr"];
const services = ["cardiologie", "pediatrie", "urgences", "chirurgie", "maternite", "radiologie"];
const diagnostics = ["hypertension", "diabete_type2", "paludisme", "grippe", "asthme", "drepanocytose", "gastro", "fracture"];

const LOT = 5000;        // insertion par paquets de 5000
const TOTAL = 100000;
let docs = [];

for (let i = 1; i <= TOTAL; i++) {
  docs.push({
    patient_id: i,
    nom: noms[Math.floor(Math.random() * noms.length)],
    prenom: prenoms[Math.floor(Math.random() * prenoms.length)],
    age: Math.floor(Math.random() * 90) + 1,
    service: services[Math.floor(Math.random() * services.length)],
    diagnostic: diagnostics[Math.floor(Math.random() * diagnostics.length)],
    date_admission: new Date(2024, Math.floor(Math.random() * 24), Math.floor(Math.random() * 28) + 1),
    hopital: "hopital_" + (Math.floor(Math.random() * 5) + 1)
  });
  if (docs.length === LOT) {
    db5.dossiers_patients.insertMany(docs);
    docs = [];
    print("Insérés : " + i + " / " + TOTAL);
  }
}
print("[OK] Génération terminée : " + db5.dossiers_patients.countDocuments() + " documents.");