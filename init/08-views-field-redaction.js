// =============================================================================
// Sécurité au niveau champ (field-level) via une VUE en lecture seule :
// MongoDB ne propose pas de RBAC nativement au niveau du champ, donc pour
// masquer des champs cliniques sensibles à un rôle donné (ici : infirmier),
// on expose une vue projetant uniquement les champs autorisés.
//
// Variables injectées via --eval : ROOT_USER, ROOT_PASSWORD, APP_DB_NAME
// =============================================================================

db.getSiblingDB("admin").auth(ROOT_USER, ROOT_PASSWORD);
const appDb = db.getSiblingDB(APP_DB_NAME);

// Recréation de la vue avec les champs harmonisés sous la nomenclature du groupe
appDb.createView("v_dossiers_patients_infirmier", "dossiers_patients", [
  {
    $project: {
      patient_id: 1,
      nom: 1,
      prenom: 1,
      date_naissance: 1,  
      allergies: 1,
      traitements_en_cours: 1,
      
      // Champs volontairement EXCLUS de cette vue (non listés donc masqués) :
      // diagnostic_detaille, antecedents_psychiatriques, notes_medecin
    },
  },
]);

print("[OK] Vue v_dossiers_patients_infirmier créée avec succès (champs cliniques sensibles masqués).");
