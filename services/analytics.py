import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    """Crée la table visits si elle n'existe pas."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS visits (
                    id SERIAL PRIMARY KEY,
                    route TEXT NOT NULL,
                    ip TEXT,
                    country TEXT,
                    user_agent TEXT,
                    device TEXT,
                    browser TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
        conn.commit()


def enregistrer_visite(route: str, ip: str, country: str, user_agent: str, device: str, browser: str):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO visits (route, ip, country, user_agent, device, browser)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (route, ip, country, user_agent, device, browser))
            conn.commit()
    except Exception as e:
        print(f"Erreur enregistrement visite : {e}")


def get_stats() -> dict:
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # Total visites
                cur.execute("SELECT COUNT(*) AS total FROM visits")
                total = cur.fetchone()["total"]

                # Visiteurs uniques (par IP)
                cur.execute("SELECT COUNT(DISTINCT ip) AS uniques FROM visits")
                uniques = cur.fetchone()["uniques"]

                # Pages vues par route
                cur.execute("""
                    SELECT route, COUNT(*) AS count
                    FROM visits
                    GROUP BY route
                    ORDER BY count DESC
                    LIMIT 10
                """)
                routes = cur.fetchall()

                # Visites par pays
                cur.execute("""
                    SELECT COALESCE(country, 'Inconnu') AS country, COUNT(*) AS count
                    FROM visits
                    GROUP BY country
                    ORDER BY count DESC
                    LIMIT 10
                """)
                pays = cur.fetchall()

                # Visites par appareil
                cur.execute("""
                    SELECT COALESCE(device, 'Inconnu') AS device, COUNT(*) AS count
                    FROM visits
                    GROUP BY device
                    ORDER BY count DESC
                """)
                devices = cur.fetchall()

                # Visites par navigateur
                cur.execute("""
                    SELECT COALESCE(browser, 'Inconnu') AS browser, COUNT(*) AS count
                    FROM visits
                    GROUP BY browser
                    ORDER BY count DESC
                    LIMIT 6
                """)
                browsers = cur.fetchall()

                # Visites par jour (30 derniers jours)
                cur.execute("""
                    SELECT DATE(created_at) AS day, COUNT(*) AS count
                    FROM visits
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY day
                    ORDER BY day ASC
                """)
                par_jour = cur.fetchall()

                # Visites aujourd'hui
                cur.execute("""
                    SELECT COUNT(*) AS count FROM visits
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
                aujourd_hui = cur.fetchone()["count"]

                # Visites cette semaine
                cur.execute("""
                    SELECT COUNT(*) AS count FROM visits
                    WHERE created_at >= NOW() - INTERVAL '7 days'
                """)
                cette_semaine = cur.fetchone()["count"]

        return {
            "total": total,
            "uniques": uniques,
            "aujourd_hui": aujourd_hui,
            "cette_semaine": cette_semaine,
            "routes": [dict(r) for r in routes],
            "pays": [dict(p) for p in pays],
            "devices": [dict(d) for d in devices],
            "browsers": [dict(b) for b in browsers],
            "par_jour": [{"day": str(r["day"]), "count": r["count"]} for r in par_jour],
        }
    except Exception as e:
        print(f"Erreur lecture stats : {e}")
        return {
            "total": 0,
            "uniques": 0,
            "aujourd_hui": 0,
            "cette_semaine": 0,
            "routes": [],
            "pays": [],
            "devices": [],
            "browsers": [],
            "par_jour": [],
            "erreur": str(e),
        }