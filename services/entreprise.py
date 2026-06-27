import requests

API_URL = "https://recherche-entreprises.api.gouv.fr/search"


def rechercher_entreprises(query: str, per_page: int = 10) -> list:
    """
    Recherche des entreprises par nom, SIRET ou SIREN.
    Retourne une liste de résultats (vide si rien trouvé).
    """
    params = {"q": query, "per_page": per_page}

    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])

    except requests.exceptions.RequestException as e:
        print(f"Erreur API entreprise : {e}")
        return []


def rechercher_entreprise_par_siren(siren: str) -> dict | None:
    """
    Récupère une entreprise précise par son SIREN.
    Retourne le premier résultat ou None.
    """
    resultats = rechercher_entreprises(siren, per_page=1)
    return resultats[0] if resultats else None