from datetime import date
from flask import Flask, render_template, request
from services.entreprise import rechercher_entreprises, rechercher_entreprise_par_siren
from services.bodacc import recuperer_annonces_bodacc
from services.risque import calculer_score_risque

app = Flask(__name__)

NATURE_JURIDIQUE = {
    "1000": "Entrepreneur individuel",
    "1100": "Artisan-commerçant",
    "1200": "Commerçant",
    "1300": "Artisan",
    "2110": "Indivision",
    "5410": "SARL",
    "5415": "EURL",
    "5499": "Société à responsabilité limitée",
    "5500": "SA",
    "5505": "SA à conseil d'administration",
    "5510": "SA à directoire",
    "5599": "Société anonyme",
    "5710": "SAS",
    "5720": "SASU",
    "5800": "Société européenne",
    "6100": "Association loi 1901",
    "6316": "Coopérative",
    "9220": "Collectivité territoriale",
}


@app.errorhandler(404)
def page_non_trouvee(e):
    return render_template("erreur.html", code=404, message="Page introuvable."), 404


@app.errorhandler(500)
def erreur_serveur(e):
    return render_template("erreur.html", code=500, message="Une erreur interne est survenue."), 500


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/resultats", methods=["GET"])
def resultats():
    query = request.args.get("q", "").strip()

    if not query:
        return render_template("index.html", erreur="Veuillez entrer un nom ou un SIRET.")

    entreprises = rechercher_entreprises(query)

    if not entreprises:
        return render_template("index.html", erreur=f"Aucune entreprise trouvée pour « {query} ».")

    if len(entreprises) == 1:
        return _afficher_rapport(entreprises[0], query)

    return render_template("resultats.html", entreprises=entreprises, query=query)


@app.route("/rapport", methods=["GET"])
def rapport():
    siren = request.args.get("siren", "").strip()
    query = request.args.get("q", "").strip()

    if not siren:
        return render_template("index.html", erreur="SIREN manquant.")

    entreprise = rechercher_entreprise_par_siren(siren)

    if not entreprise:
        return render_template("index.html", erreur=f"Entreprise introuvable pour le SIREN {siren}.")

    return _afficher_rapport(entreprise, query)


def _afficher_rapport(entreprise: dict, query: str):
    siren = entreprise.get("siren", "")
    bodacc = recuperer_annonces_bodacc(siren)
    risque = calculer_score_risque(entreprise, bodacc)
    code = str(entreprise.get("nature_juridique", "") or "")
    nature = NATURE_JURIDIQUE.get(code, f"Code {code}" if code else "—")

    return render_template(
        "rapport.html",
        entreprise=entreprise,
        nature_juridique=nature,
        risque=risque,
        bodacc=bodacc,
        query=query,
        date_rapport=date.today().strftime("%d/%m/%Y"),
    )


if __name__ == "__main__":
    app.run(debug=True)