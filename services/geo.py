import requests


def get_country(ip: str) -> str:
    """Détecte le pays via l'IP avec ip-api.com (gratuit, sans clé)."""
    if not ip or ip in ("127.0.0.1", "::1"):
        return "Local"
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=country", timeout=3)
        data = response.json()
        return data.get("country", "Inconnu")
    except Exception:
        return "Inconnu"


def parse_device(user_agent: str) -> str:
    """Détecte le type d'appareil à partir du User-Agent."""
    ua = (user_agent or "").lower()
    if any(x in ua for x in ("iphone", "android", "mobile", "blackberry", "windows phone")):
        return "Mobile"
    if any(x in ua for x in ("ipad", "tablet")):
        return "Tablette"
    return "Desktop"


def parse_browser(user_agent: str) -> str:
    """Détecte le navigateur à partir du User-Agent."""
    ua = (user_agent or "").lower()
    if "edg/" in ua or "edge/" in ua:
        return "Edge"
    if "opr/" in ua or "opera" in ua:
        return "Opera"
    if "chrome/" in ua and "chromium" not in ua:
        return "Chrome"
    if "firefox/" in ua:
        return "Firefox"
    if "safari/" in ua and "chrome" not in ua:
        return "Safari"
    if "msie" in ua or "trident/" in ua:
        return "Internet Explorer"
    return "Autre"