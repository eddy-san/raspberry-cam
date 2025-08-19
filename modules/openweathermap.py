import requests

def get_openweathermap(cfg: dict) -> dict:
    api_key = cfg.get("openweathermap_api_key")
    if not api_key:
        return {"error": "API key fehlt in der Konfiguration!"}

    city = cfg.get("city", "Laufamholz,de")
    url = (
        "http://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={api_key}&units=metric"
    )

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {"error": f"API request failed: {resp.text}"}
        return resp.json()
    except requests.Timeout:
        return {"error": "OpenWeatherMap API not available at this timepoint (timeout)"}
    except requests.RequestException as e:
        return {"error": f"OpenWeatherMap API not available at this timepoint ({e})"}
