#!/usr/bin/env python3
"""
generate_dataset.py
--------------------
Génère un jeu de données réaliste pour le use case "Plateforme Centrale de
Centralisation de Logs Médicaux" (Devoir MongoDB - Master IA).

Génère des documents alignés sur le schéma réellement utilisé par le cluster
sécurisé/shardé du projet (voir init/07-sharding-collections.js et
init/08-views-field-redaction.js) :
  - hopital_db.dossiers_patients (shardée sur patient_id hashed)
  - hopital_db.resultats_labo    (shardée sur patient_id hashed)
  - hopital_db.suivi_soins       (utilisée par le rôle infirmier)
  - audit_db.access_logs         (utilisée par le rôle auditeur)

Usage rapide (fichiers JSON, aucune dépendance au cluster) :
    python3 generate_dataset.py --num-patients 300

Insertion directe dans le cluster sécurisé (via mongos, TLS + auth) :
    python3 generate_dataset.py --num-patients 300 --insert-mongo
"""

import argparse
import json
import os
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
HOPITAUX_IDS = list(REGIONS_HOPITAUX.keys())
HOPITAUX_POIDS = [30, 20, 15, 8, 7, 7, 6, 7]

GROUPES_SANGUINS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
ALLERGIES_POSSIBLES = [
    "Pénicilline", "Arachides", "Latex", "Iode", "Aspirine", "Pollen",
    "Fruits de mer", "Sulfamides",
]

# Diagnostics en texte libre : phrases réalistes pour tester les Text Indexes.
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

ANTECEDENTS_PSY_POSSIBLES = [
    "Aucun antécédent particulier",
    "Aucun antécédent particulier",
    "Aucun antécédent particulier",
    "Suivi pour trouble anxieux généralisé",
    "Antécédent dépressif documenté, sous traitement",
    "Antécédent de trouble bipolaire stabilisé",
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


def generer_dossier_patient(index):
    """Un document = le dossier patient complet (schéma attendu par
    init/08-views-field-redaction.js : la vue infirmier masque
    diagnostic_detaille, antecedents_psychiatriques et notes_medecin)."""
    sexe = random.choice(["M", "F"])
    prenom = random.choice(PRENOMS_H if sexe == "M" else PRENOMS_F)
    nom = random.choice(NOMS_FAMILLE)
    hopital_id = choisir_hopital()
    infos_hopital = REGIONS_HOPITAUX[hopital_id]

    # Quelques patients "chauds" (10%) : dossier plus étoffé, utile pour
    # simuler une charge réaliste.
    est_patient_chaud = random.random() < 0.10

    return {
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
        "traitements_en_cours": random.sample(
            TRAITEMENTS_POSSIBLES, k=random.randint(1, 3)
        ),
        # Champs cliniques sensibles, masqués pour le rôle infirmier par la
        # vue v_dossiers_patients_infirmier :
        "diagnostic_detaille": random.choice(DIAGNOSTICS),
        "antecedents_psychiatriques": random.choice(ANTECEDENTS_PSY_POSSIBLES),
        "notes_medecin": fake.sentence(nb_words=12),
        "est_patient_chaud": est_patient_chaud,
        "created_at": date_aleatoire(annees_passees=5),
        "updated_at": datetime.now(),
    }


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


def generer_suivi_soins_pour_patient(patient):
    """Constantes/soins courants : collection dédiée à l'infirmier
    (find/insert/update dans role_infirmier, séparée du dossier complet)."""
    nb = random.randint(2, 5)
    soins = []
    for _ in range(nb):
        soins.append({
            "patient_id": patient["patient_id"],
            "date": date_aleatoire(annees_passees=2),
            "infirmier_id": f"INF-{random.randint(1, 100):04d}",
            "constantes": {
                "tension_arterielle": f"{random.randint(10, 16)}/{random.randint(6, 10)}",
                "temperature_c": round(random.uniform(36.0, 39.5), 1),
                "pouls_bpm": random.randint(55, 115),
            },
            "notes_soins": fake.sentence(nb_words=8),
        })
    return soins


def generer_logs_pour_patient(patient, nb_min=5, nb_max=20):
    """Journal d'accès applicatif (audit_db.access_logs, lu par
    role_auditeur_securite / alimenté par role_app_watcher)."""
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
    parser = argparse.ArgumentParser(
        description="Génère des données de test pour hopital_db / audit_db"
    )
    parser.add_argument("--num-patients", type=int, default=300, help="Nombre de patients à générer")
    parser.add_argument("--output-dir", type=str, default="./dataset", help="Dossier de sortie pour les fichiers JSON")
    parser.add_argument("--seed", type=int, default=42, help="Graine aléatoire pour la reproductibilité")

    parser.add_argument("--insert-mongo", action="store_true",
                         help="Insère directement dans le cluster sécurisé (via mongos) au lieu d'écrire des fichiers JSON")
    parser.add_argument("--host", type=str, default="localhost", help="Hôte de mongos (utilisé avec --insert-mongo)")
    parser.add_argument("--port", type=int, default=27020, help="Port exposé de mongos sur l'hôte (27020, voir docker-compose.yml)")
    parser.add_argument("--username", type=str, default="admin_root", help="Utilisateur MongoDB (créé par init/04-create-admin-users.js)")
    parser.add_argument("--password", type=str, default="SuperSecretRootPassword2026", help="Mot de passe associé")
    parser.add_argument("--auth-source", type=str, default="admin", help="Base d'authentification de l'utilisateur")
    parser.add_argument("--tls-cert", type=str, default="./certs/admin-client.pem", help="Certificat client TLS (mutual TLS requis par requireTLS)")
    parser.add_argument("--tls-ca", type=str, default="./certs/ca.pem", help="Certificat de la CA du cluster")
    parser.add_argument("--db-name", type=str, default="hopital_db", help="Base applicative cible (dossiers_patients / resultats_labo / suivi_soins)")
    parser.add_argument("--audit-db-name", type=str, default="audit_db", help="Base d'audit cible (access_logs)")
    args = parser.parse_args()

    random.seed(args.seed)
    Faker.seed(args.seed)

    print(f"Génération de {args.num_patients} patients...")

    dossiers_patients, resultats_labo, suivi_soins, access_logs = [], [], [], []

    for i in range(1, args.num_patients + 1):
        patient = generer_dossier_patient(i)
        dossiers_patients.append(patient)
        resultats_labo.extend(generer_resultats_labo_pour_patient(patient))
        suivi_soins.extend(generer_suivi_soins_pour_patient(patient))
        access_logs.extend(generer_logs_pour_patient(patient))

        if i % 1000 == 0:
            print(f"  ... {i}/{args.num_patients} patients traités")

    print("\nRésumé du dataset généré :")
    print(f"  dossiers_patients (hopital_db) : {len(dossiers_patients)}")
    print(f"  resultats_labo    (hopital_db) : {len(resultats_labo)}")
    print(f"  suivi_soins       (hopital_db) : {len(suivi_soins)}")
    print(f"  access_logs       (audit_db)   : {len(access_logs)}")

    if args.insert_mongo:
        import pymongo

        print(f"\nConnexion à mongos : {args.host}:{args.port} (TLS + auth, utilisateur '{args.username}')")
        client = pymongo.MongoClient(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            authSource=args.auth_source,
            tls=True,
            tlsCertificateKeyFile=args.tls_cert,
            tlsCAFile=args.tls_ca,
            serverSelectionTimeoutMS=5000,
        )
        # Force la connexion tout de suite pour échouer vite avec un message clair
        client.admin.command("ping")

        app_db = client[args.db_name]
        audit_db = client[args.audit_db_name]

        # On n'utilise PAS drop() sur dossiers_patients/resultats_labo : ce
        # sont des collections déjà shardées (init/07-sharding-collections.js).
        # Un drop() les recréerait comme collections NON shardées à la
        # prochaine écriture. On insère donc en complément des données
        # existantes.
        collections_app = {
            "dossiers_patients": dossiers_patients,
            "resultats_labo": resultats_labo,
            "suivi_soins": suivi_soins,
        }
        for nom_collection, documents in collections_app.items():
            for i in range(0, len(documents), 1000):
                lot = documents[i:i + 1000]
                app_db[nom_collection].insert_many(lot)
            print(f"  -> {len(documents)} documents insérés dans '{args.db_name}.{nom_collection}'")

        for i in range(0, len(access_logs), 1000):
            lot = access_logs[i:i + 1000]
            audit_db["access_logs"].insert_many(lot)
        print(f"  -> {len(access_logs)} documents insérés dans '{args.audit_db_name}.access_logs'")

        print("\nInsertion terminée dans MongoDB.")
    else:
        os.makedirs(args.output_dir, exist_ok=True)

        ecrire_json(os.path.join(args.output_dir, "dossiers_patients.json"), dossiers_patients)
        ecrire_json(os.path.join(args.output_dir, "resultats_labo.json"), resultats_labo)
        ecrire_json(os.path.join(args.output_dir, "suivi_soins.json"), suivi_soins)
        ecrire_json(os.path.join(args.output_dir, "access_logs.json"), access_logs)

        print(f"\nFichiers JSON écrits dans : {args.output_dir}/")
        print("  - dossiers_patients.json")
        print("  - resultats_labo.json")
        print("  - suivi_soins.json")
        print("  - access_logs.json")


if __name__ == "__main__":
    main()
