from datetime import datetime

# Codes NAF typiques des micro-entreprises / auto-entrepreneurs
# (activités de services aux personnes, conseil, freelance)
CATEGORIES_JURIDIQUES_MICRO = {"1000", "5499", "5410"}  # EI, EIRL, micro


def _est_micro_entreprise(entreprise: dict) -> bool:
    """
    Détecte si l'entreprise est une micro-entreprise / entreprise individuelle.
    L'API retourne nature_juridique sous forme de code INSEE (ex: '1000' = EI).
    Codes commençant par '1' = personnes physiques (EI, micro, auto-entrepreneur).
    """
    nature = str(entreprise.get("nature_juridique", "") or "")
    categorie = str(entreprise.get("categorie_juridique", "") or "")
    return (
        nature.startswith("1")    # Code INSEE : 1xxx = Entrepreneur individuel
        or categorie.startswith("1")
    )


def calculer_score_risque(entreprise: dict, bodacc: dict | None = None) -> dict:
    """
    Calcule un score de risque basé sur les données publiques et le BODACC.
    Score de 0 (aucun risque) à 100 (risque maximal).
    """
    score = 0
    signaux = []
    micro = _est_micro_entreprise(entreprise)

    # -------------------------------------------------------
    # 1. BODACC — procédures collectives (poids maximal)
    # -------------------------------------------------------
    if bodacc:
        procedures = bodacc.get("procedures", [])

        for proc in procedures:
            label = proc.get("label", "Procédure")
            date = proc.get("date", "")
            date_str = f" ({date})" if date else ""
            gravite = proc.get("gravite", "modere")

            if gravite == "critique":
                score += 60
                signaux.append(("danger", f"{label} publiée au BODACC{date_str}"))
            elif gravite == "grave":
                score += 35
                signaux.append(("danger", f"{label} publiée au BODACC{date_str}"))
            else:
                score += 20
                signaux.append(("warning", f"{label} publiée au BODACC{date_str}"))

        if not procedures and bodacc.get("erreur") is None:
            signaux.append(("ok", "Aucune procédure collective au BODACC"))

        if bodacc.get("erreur"):
            signaux.append(("warning", "Données BODACC indisponibles"))

    # -------------------------------------------------------
    # 2. Statut administratif (cessée = fort signal)
    # -------------------------------------------------------
    etat = entreprise.get("etat_administratif", "")
    if etat == "C":
        score += 35
        signaux.append(("danger", "Entreprise cessée (radiée)"))
    elif etat == "A":
        signaux.append(("ok", "Entreprise active"))

    # -------------------------------------------------------
    # 3. Ancienneté
    # -------------------------------------------------------
    date_creation = entreprise.get("date_creation")
    if date_creation:
        try:
            creation = datetime.strptime(date_creation, "%Y-%m-%d")
            anciennete = (datetime.now() - creation).days / 365
            if anciennete < 1:
                score += 20
                signaux.append(("danger", "Entreprise créée il y a moins d'un an"))
            elif anciennete < 3:
                score += 10
                signaux.append(("warning", "Entreprise créée il y a moins de 3 ans"))
            else:
                signaux.append(("ok", f"Entreprise ancienne ({int(anciennete)} ans)"))
        except ValueError:
            pass

    # -------------------------------------------------------
    # 4. Effectif (non pénalisé pour les micro-entreprises)
    # -------------------------------------------------------
    tranche = entreprise.get("tranche_effectif_salarie", "")
    if not micro:
        if tranche in ("", "NN", None):
            score += 10
            signaux.append(("warning", "Effectif non renseigné"))
        else:
            signaux.append(("ok", "Effectif renseigné"))

    # -------------------------------------------------------
    # 5. Siège social
    # -------------------------------------------------------
    siege = entreprise.get("siege", {})
    if not siege:
        score += 5
        signaux.append(("warning", "Siège social non renseigné"))

    # -------------------------------------------------------
    # Niveau final — inversion : 100 = aucun risque, 0 = risque maximal
    # -------------------------------------------------------
    score = 100 - min(score, 100)

    if score <= 40:
        niveau = "Élevé"
        couleur = "red"
    elif score <= 75:
        niveau = "Modéré"
        couleur = "orange"
    else:
        niveau = "Faible"
        couleur = "green"

    return {
        "score": score,
        "niveau": niveau,
        "couleur": couleur,
        "signaux": signaux,
        "micro": micro,
    }