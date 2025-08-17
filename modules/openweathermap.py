import requests

def getOpenweathermapData(weather_json: dict, cfg: dict):
    api_key = cfg.get("openweathermap_api_key")
    if not api_key:
        raise ValueError("API key fehlt in der Konfiguration!")

    # Ort auf Laufamholz, Deutschland setzen (falls nichts anderes in cfg steht)
    city = cfg.get("city", "Laufamholz,de")

    url = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={api_key}&units=metric"
    )

    try:
        response = requests.get(url, timeout=10)  # Timeout 10 Sekunden
        if response.status_code != 200:
            weather_json["openweathermap"] = {
                "error": f"API request failed: {response.text}"
            }
            return

        data = response.json()
        weather_json.update(data)

    except requests.Timeout:
        weather_json["openweathermap"] = {
            "error": "OpenWeatherMap API not available at this timepoint (timeout)"
        }
    except requests.RequestException as e:
        weather_json["openweathermap"] = {
            "error": f"OpenWeatherMap API not available at this timepoint ({e})"
        }
