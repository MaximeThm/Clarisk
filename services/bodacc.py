import requests

API_URL = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"

PROCEDURES = [
    ("LIQUIDATION_JUDICIAIRE", "Liquidation judiciaire",   ["liquidation judiciaire", "liquidation"],          "critique"),
    ("REDRESSEMENT_JUDICIAIRE","Redressement judiciaire",  ["redressement judiciaire", "redressement"],        "critique"),
    ("SAUVEGARDE",             "Procédure de sauvegarde",  ["sauvegarde"],                                     "critique"),
    ("PROCEDURE_COLLECTIVE",   "Procédure collective",     ["procédures collectives", "procedure collective"], "critique"),
    ("PLAN_REDRESSEMENT",      "Plan de redressement",     ["plan de redressement"],                           "grave"),
    ("PLAN_SAUVEGARDE",        "Plan de sauvegarde",       ["plan de sauvegarde"],                             "grave"),
    ("CESSION",                "Cession d'activité",       ["cession", "vente"],                               "grave"),
    ("DISSOLUTION",            "Dissolution",              ["dissolution"],                                     "modere"),
    ("RADIATION",              "Radiation",                ["radiation"],                                       "modere"),
]


def recuperer_annonces_bodacc(siren: str) -> dict:
    if not siren:
        return {"annonces": [], "procedures": [], "erreur": "SIREN manquant"}

    params = {
        "where": f'registre like "{siren}"',
        "order_by": "dateparution desc",
        "limit": 20,
    }

    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        annonces = data.get("results", [])
        procedures = _detecter_procedures(annonces)
        return {"annonces": annonces, "procedures": procedures, "erreur": None}

    except requests.exceptions.RequestException as e:
        print(f"Erreur API BODACC : {e}")
        return {"annonces": [], "procedures": [], "erreur": str(e)}


def _detecter_procedures(annonces: list) -> list:
    procedures = []
    vues = set()

    for annonce in annonces:
        texte = " ".join([
            (annonce.get("familleavis_lib") or ""),
            (annonce.get("typeavis_lib") or ""),
            (annonce.get("commercant") or ""),
        ]).lower()

        for type_interne, label, mots_cles, gravite in PROCEDURES:
            if type_interne in vues:
                continue
            if any(mot in texte for mot in mots_cles):
                procedures.append({
                    "type": type_interne,
                    "label": label,
                    "gravite": gravite,
                    "date": annonce.get("dateparution", ""),
                })
                vues.add(type_interne)

    return procedures