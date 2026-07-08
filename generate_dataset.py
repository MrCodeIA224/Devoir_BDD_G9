#!/usr/bin/env python3
"""
generate_dataset.py
--------------------
Génère un jeu de données réaliste pour le use case "Plateforme Centrale de
Centralisation de Logs Médicaux" (Devoir MongoDB - Master IA).

Génère 4 collections :
  - patients
  - consultations
  - resultats_labo
  - logs_acces


Usage rapide :
    python3 generate_dataset.py --num-patients 50000

"""

import argparse
import json
import random
from datetime import datetime, timedelta

from faker import Faker

fake = Faker("fr_FR")

# ----------------------------------------------------------------------------
# Données de référence "Sénégal" pour rendre le dataset crédible
# ----------------------------------------------------------------------------

PRENOMS_H = [
    "Mamadou", "Ibrahima", "Ousmane", "Moussa", "Cheikh", "Abdoulaye", "Modou",
    "Alioune", "Babacar", "Serigne", "Amadou", "Mor", "Pape", "Ibrahim", "Malick",
]
PRENOMS_F = [
    "Awa", "Fatou", "Aminata", "Aissatou", "Khady", "Ndeye", "Mariama", "Bineta",
    "Coumba", "Adja", "Rokhaya", "Astou", "Sokhna", "Ndeye Fatou", "Marieme",
]
NOMS_FAMILLE = [
    "Diop", "Ndiaye", "Fall", "Sow", "Gueye", "Diallo", "Ba", "Sarr", "Diagne",
    "Faye", "Mbaye", "Thiam", "Cisse", "Toure", "Kane", "Seck", "Sy", "Dieng",
    "Ndoye", "Camara",
]

REGIONS_HOPITAUX = {
    "HOP-DKR-01": {"nom": "Hôpital Principal de Dakar", "ville": "Dakar", "region": "Dakar"},
    "HOP-DKR-02": {"nom": "Hôpital Aristide Le Dantec", "ville": "Dakar", "region": "Dakar"},
    "HOP-DKR-03": {"nom": "Hôpital Fann", "ville": "Dakar", "region": "Dakar"},
    "HOP-THS-01": {"nom": "Hôpital Régional de Thiès", "ville": "Thiès", "region": "Thiès"},
    "HOP-STL-01": {"nom": "Hôpital Régional de Saint-Louis", "ville": "Saint-Louis", "region": "Saint-Louis"},
    "HOP-KLK-01": {"nom": "Hôpital Régional de Kaolack", "ville": "Kaolack", "region": "Kaolack"},
    "HOP-ZGC-01": {"nom": "Hôpital Régional de Ziguinchor", "ville": "Ziguinchor", "region": "Ziguinchor"},
    "HOP-TBA-01": {"nom": "Hôpital Régional de Touba", "ville": "Touba", "region": "Diourbel"},
}
# Poids volontairement inégaux : Dakar concentre plus de patients.
# Utile pour tester une clé de sharding par zone (region) chez Personne A.
HOPITAUX_IDS = list(REGIONS_HOPITAUX.keys())
HOPITAUX_POIDS = [30, 20, 15, 8, 7, 7, 6, 7]

GROUPES_SANGUINS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
ALLERGIES_POSSIBLES = [
    "Pénicilline", "Arachides", "Latex", "Iode", "Aspirine", "Pollen",
    "Fruits de mer", "Sulfamides",
]

# Diagnostics en texte libre : phrases réalistes pour tester les Text Indexes
# (Partie 5 - Personne C). On varie volontairement le vocabulaire médical.
DIAGNOSTICS = [
    "Suspicion de diabète type 2, glycémie à jeun élevée, mise sous metformine",
    "Hypertension artérielle non contrôlée, ajustement du traitement antihypertenseur",
    "Paludisme confirmé par goutte épaisse, traitement par ACT initié",
    "Infection respiratoire aiguë basse, toux productive depuis 5 jours",
    "Suivi de grossesse, troisième trimestre, absence de complication",
    "Douleurs abdominales aiguës, suspicion d'appendicite, avis chirurgical demandé",
    "Anémie ferriprive sévère, supplémentation en fer prescrite",
    "Consultation de routine, bilan lipidique demandé, patient asymptomatique",
    "Crise drépanocytaire, hospitalisation pour hydratation et antalgiques",
    "Suivi post-opératoire, cicatrisation satisfaisante, ablation des fils",
    "Diarrhée aiguë avec déshydratation modérée chez l'enfant",
    "Suspicion de tuberculose pulmonaire, recherche de BK dans les crachats",
    "Céphalées chroniques, bilan neurologique normal, migraine probable",
    "Consultation dermatologique pour lésions cutanées suspectes",
    "Suivi diabétique de routine, HbA1c stable, poursuite du traitement",
    "Traumatisme suite à un accident de la route, fracture du tibia suspectée",
    "Infection urinaire basse, antibiothérapie probabiliste débutée",
    "Bilan cardiovasculaire de routine, ECG normal, aucune anomalie détectée",
    "Suivi VIH, charge virale indétectable, bonne observance du traitement",
    "Consultation pédiatrique, retard de croissance à surveiller",
]

TRAITEMENTS_POSSIBLES = [
    "Metformine 500mg", "Amlodipine 5mg", "Artéméther-luméfantrine",
    "Amoxicilline 1g", "Paracétamol 1g", "Fer + acide folique",
    "Insuline rapide", "Oméprazole 20mg", "Ibuprofène 400mg",
    "Cotrimoxazole", "Vitamine D3", "Salbutamol inhalé",
]

TYPES_ANALYSE = [
    "Glycémie à jeun", "Hémogramme complet (NFS)", "Créatininémie",
    "Bilan lipidique", "Test de la goutte épaisse (paludisme)",
    "Sérologie VIH", "Groupage sanguin", "Bilan hépatique", "CRP",
    "Analyse d'urine (ECBU)",
]

ROLES_UTILISATEURS = ["medecin", "infirmier", "administrateur", "laborantin"]
ACTIONS_LOG = ["lecture_dossier", "modification_dossier", "creation_document", "export_donnees"]
RESULTATS_LOG_POIDS = [("autorise", 92), ("refuse", 8)]


def choix_pondere(options_poids):
    options, poids = zip(*options_poids)
    return random.choices(options, weights=poids, k=1)[0]


def choisir_hopital():
    return random.choices(HOPITAUX_IDS, weights=HOPITAUX_POIDS, k=1)[0]


def date_aleatoire(annees_passees=5):
    debut = datetime.now() - timedelta(days=365 * annees_passees)
    delta_jours = random.randint(0, 365 * annees_passees)
    return debut + timedelta(days=delta_jours)


def generer_patient(index):
    sexe = random.choice(["M", "F"])
    prenom = random.choice(PRENOMS_H if sexe == "M" else PRENOMS_F)
    nom = random.choice(NOMS_FAMILLE)
    hopital_id = choisir_hopital()
    infos_hopital = REGIONS_HOPITAUX[hopital_id]

    # Quelques patients "chauds" (10%) auront beaucoup plus de consultations
    # -> utile pour simuler une charge réaliste et tester les performances.
    est_patient_chaud = random.random() < 0.10

    return {
        "_id_logique": f"PAT-{index:06d}",
        "patient_id": f"PAT-{index:06d}",
        "nom": nom,
        "prenom": prenom,
        "sexe": sexe,
        "date_naissance": date_aleatoire(annees_passees=80 - 60) - timedelta(days=365 * 20),
        "groupe_sanguin": random.choice(GROUPES_SANGUINS),
        "allergies": random.sample(ALLERGIES_POSSIBLES, k=random.randint(0, 2)),
        "adresse": {
            "ville": infos_hopital["ville"],
            "region": infos_hopital["region"],
        },
        "hopital_reference": hopital_id,
        "est_patient_chaud": est_patient_chaud,
        "created_at": date_aleatoire(annees_passees=5),
        "updated_at": datetime.now(),
    }


def generer_consultations_pour_patient(patient):
    nb = random.randint(15, 30) if patient["est_patient_chaud"] else random.randint(3, 10)
    consultations = []
    for _ in range(nb):
        consultations.append({
            "patient_id": patient["patient_id"],
            "medecin_id": f"MED-{random.randint(1, 200):04d}",
            "hopital_id": patient["hopital_reference"],
            "date": date_aleatoire(annees_passees=5),
            "diagnostic": random.choice(DIAGNOSTICS),
            "traitement_prescrit": random.sample(
                TRAITEMENTS_POSSIBLES, k=random.randint(1, 3)
            ),
            "type_document": "consultation",
        })
    return consultations


def generer_resultats_labo_pour_patient(patient):
    nb = random.randint(2, 6)
    resultats = []
    for _ in range(nb):
        type_analyse = random.choice(TYPES_ANALYSE)
        resultats.append({
            "patient_id": patient["patient_id"],
            "date_prelevement": date_aleatoire(annees_passees=5),
            "type_analyse": type_analyse,
            "valeurs": {
                "resultat": round(random.uniform(0.5, 2.5), 2),
                "unite": "g/L",
            },
            "laboratoire_id": f"LAB-{random.randint(1, 20):03d}",
        })
    return resultats


def generer_logs_pour_patient(patient, nb_min=5, nb_max=20):
    nb = random.randint(nb_min, nb_max)
    logs = []
    for _ in range(nb):
        role = random.choice(ROLES_UTILISATEURS)
        logs.append({
            "utilisateur_id": f"USR-{random.randint(1, 300):04d}",
            "role": role,
            "patient_id_consulte": patient["patient_id"],
            "action": random.choice(ACTIONS_LOG),
            "date_heure": date_aleatoire(annees_passees=2),
            "ip_source": fake.ipv4(),
            "resultat": choix_pondere(RESULTATS_LOG_POIDS),
        })
    return logs


def _default_json(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type non sérialisable : {type(obj)}")


def ecrire_json(chemin, documents):
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2, default=_default_json)


def main():
    parser = argparse.ArgumentParser(description="Génère le jeu de données patients/consultations/labo/logs")
    parser.add_argument("--num-patients", type=int, default=10000, help="Nombre de patients à générer")
    parser.add_argument("--output-dir", type=str, default="./dataset", help="Dossier de sortie pour les fichiers JSON")
    parser.add_argument("--seed", type=int, default=42, help="Graine aléatoire pour la reproductibilité")
    parser.add_argument("--insert-mongo", action="store_true", help="Insère directement dans MongoDB au lieu d'écrire des fichiers JSON")
    parser.add_argument("--mongo-uri", type=str, default="mongodb://localhost:27017", help="URI de connexion MongoDB (utilisé avec --insert-mongo)")
    parser.add_argument("--db-name", type=str, default="dossier_patient_partage", help="Nom de la base MongoDB cible")
    args = parser.parse_args()

    random.seed(args.seed)
    Faker.seed(args.seed)

    print(f"Génération de {args.num_patients} patients...")

    patients, consultations, resultats_labo, logs_acces = [], [], [], []

    for i in range(1, args.num_patients + 1):
        patient = generer_patient(i)
        patients.append(patient)
        consultations.extend(generer_consultations_pour_patient(patient))
        resultats_labo.extend(generer_resultats_labo_pour_patient(patient))
        logs_acces.extend(generer_logs_pour_patient(patient))

        if i % 1000 == 0:
            print(f"  ... {i}/{args.num_patients} patients traités")

    # On retire le champ technique interne avant export
    for p in patients:
        p.pop("_id_logique", None)

    print("\nRésumé du dataset généré :")
    print(f"  patients        : {len(patients)}")
    print(f"  consultations   : {len(consultations)}")
    print(f"  resultats_labo  : {len(resultats_labo)}")
    print(f"  logs_acces      : {len(logs_acces)}")

    if args.insert_mongo:
        import pymongo

        print(f"\nConnexion à MongoDB : {args.mongo_uri}")
        client = pymongo.MongoClient(args.mongo_uri)
        db = client[args.db_name]

        collections = {
            "patients": patients,
            "consultations": consultations,
            "resultats_labo": resultats_labo,
            "logs_acces": logs_acces,
        }

        for nom_collection, documents in collections.items():
            db[nom_collection].drop()
            # Insertion par lots de 1000 pour éviter de saturer la mémoire/réseau
            for i in range(0, len(documents), 1000):
                lot = documents[i:i + 1000]
                db[nom_collection].insert_many(lot)
            print(f"  -> {len(documents)} documents insérés dans '{nom_collection}'")

        print("\nInsertion terminée dans MongoDB.")
        print(f"Base : {args.db_name}")
    else:
        import os
        os.makedirs(args.output_dir, exist_ok=True)

        ecrire_json(os.path.join(args.output_dir, "patients.json"), patients)
        ecrire_json(os.path.join(args.output_dir, "consultations.json"), consultations)
        ecrire_json(os.path.join(args.output_dir, "resultats_labo.json"), resultats_labo)
        ecrire_json(os.path.join(args.output_dir, "logs_acces.json"), logs_acces)

        print(f"\nFichiers JSON écrits dans : {args.output_dir}/")
        print("  - patients.json")
        print("  - consultations.json")
        print("  - resultats_labo.json")
        print("  - logs_acces.json")


if __name__ == "__main__":
    main()
