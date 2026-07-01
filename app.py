import os
from datetime import date
from datetime import date as date_cls
from functools import wraps
from flask import Flask, render_template, request, session, redirect, url_for
from services.entreprise import rechercher_entreprises, rechercher_entreprise_par_siren
from services.bodacc import recuperer_annonces_bodacc
from services.risque import calculer_score_risque
from services.analytics import init_db, enregistrer_visite, get_stats
from services.geo import get_country, parse_device, parse_browser
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD")

# Routes à ne PAS tracer (dashboard, assets, etc.)
ROUTES_IGNOREES = {"/dashboard", "/dashboard/login", "/dashboard/logout", "/favicon.ico",
                    "/mentions-legales", "/cgu", "/confidentialite", "/robots.txt", "/sitemap.xml"}

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

# -------------------------------------------------------
# Initialisation DB au démarrage
# -------------------------------------------------------
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"Impossible d'initialiser la DB analytics : {e}")


# -------------------------------------------------------
# Middleware : enregistrement des visites
# -------------------------------------------------------
BOTS = ("bot", "crawler", "spider", "curl", "wget", "python-requests",
        "googlebot", "bingbot", "slurp", "duckduckbot", "facebookexternalhit")

@app.before_request
def tracker_visite():
    route = request.path
    if route in ROUTES_IGNOREES or route.startswith("/static"):
        return

    # Ne pas compter le propriétaire connecté au dashboard
    if session.get("dashboard_ok"):
        return

    # IP réelle (derrière un proxy Render)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()

    ua = request.headers.get("User-Agent", "")

    # Ne pas compter les bots
    if any(bot in ua.lower() for bot in BOTS):
        return
    country = get_country(ip)
    device = parse_device(ua)
    browser = parse_browser(ua)

    enregistrer_visite(
        route=route,
        ip=ip,
        country=country,
        user_agent=ua,
        device=device,
        browser=browser,
    )


# -------------------------------------------------------
# Authentification dashboard
# -------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("dashboard_ok"):
            return redirect(url_for("dashboard_login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/dashboard/login", methods=["GET", "POST"])
def dashboard_login():
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["dashboard_ok"] = True
            return redirect(url_for("dashboard"))
        return render_template("dashboard_login.html", erreur="Mot de passe incorrect.")
    return render_template("dashboard_login.html")


@app.route("/dashboard/logout")
def dashboard_logout():
    session.pop("dashboard_ok", None)
    return redirect(url_for("dashboard_login"))


@app.route("/dashboard")
@login_required
def dashboard():
    stats = get_stats()
    return render_template("dashboard.html", stats=stats)

@app.route("/mentions-legales")
def mentions_legales():
    return render_template("mentions-legales.html", date_maj=date_cls.today().strftime("%d/%m/%Y"))

@app.route("/cgu")
def cgu():
    return render_template("cgu.html", date_maj=date_cls.today().strftime("%d/%m/%Y"))

@app.route("/confidentialite")
def confidentialite():
    return render_template("confidentialite.html", date_maj=date_cls.today().strftime("%d/%m/%Y"))

@app.route("/robots.txt")
def robots_txt():
    return send_from_directory(app.root_path, "robots.txt", mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap_xml():
    return send_from_directory(app.root_path, "sitemap.xml", mimetype="application/xml")

# -------------------------------------------------------
# Gestionnaires d'erreurs
# -------------------------------------------------------
@app.errorhandler(404)
def page_non_trouvee(e):
    return render_template("erreur.html", code=404, message="Page introuvable."), 404


@app.errorhandler(500)
def erreur_serveur(e):
    return render_template("erreur.html", code=500, message="Une erreur interne est survenue."), 500


# -------------------------------------------------------
# Routes principales
# -------------------------------------------------------
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