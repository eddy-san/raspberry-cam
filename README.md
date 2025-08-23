# Raspberry Pi Webcam Cloud Classification

This project enables capturing webcam images, automatic archiving, fetching weather data from OpenWeatherMap, and classifying the cloud situation.  
All results are saved as JSON files and additionally organized in a `classified` folder to prepare training data for Machine Learning.

## Features

### 📸 Image Capture & Archiving
- Capture a webcam image via a shell script (`02_take_webcam_picture.sh`).
- Current image is stored in `jpg/current/IMG_4903.jpg`.
- All captures are archived into `jpg/old/<timestamp>.jpg`.

### 🌅 Daylight Gate (No Night Shots)
- New script `00_daylight_gate.sh` uses **sunwait** to calculate **civil dawn** and **civil dusk** based on your coordinates.
- `02_take_webcam_picture.sh` calls this gate before capturing an image.
- If it is **night** (before dawn or after dusk), the script exits with code `3` → no image and no JSON are generated.
- Ensures that only **daylight captures** are taken, avoiding useless black night shots.

### 🌦️ Weather Data (OpenWeatherMap)
- New module `openweathermap.py` fetches current weather data based on the configuration (`config.local.json`).
- API key & city (`Laufamholz,de`) are loaded from the config file.
- Timeout handling: if the API does not respond, an error message is written into the JSON object.

### ☁️ Cloud Classification (Rule-based)
- New module `classify.py` creates a simple English cloud classification from OWM data:
  - `clouds.all` → cloud coverage (clear, few, scattered, broken, overcast)
  - `weather.id` → phenomenon (rain, snow, thunderstorm, drizzle, fog, …)
  - `wind.speed` → if ≥ 17 m/s, `(storm)` is added
- Output:
  - `classification`: compact string, e.g. `"overcast clouds with rain"`
  - `classification_detail`: structured details (`coverage`, `phenomenon`, `storm`, `wind_speed_ms`, `clouds_percent`, `weather_id`).

### ⚡ Storm Warning (Automaton)
- New module `stormwarning.py` implements a **finite state automaton** with three states:
  - `OK` → normal conditions
  - `WATCH` → strong wind (≥ 13 m/s by default)
  - `STORM` → storm alert (≥ 17 m/s by default)
- The automaton:
  - Reads wind data (`wind.speed` or `classification_detail.wind_speed_ms`) from the JSON object.
  - Transitions between states based on thresholds.
  - Persists its state in `json/stormwarning/storm_state.json`.
  - Sends an **email notification via SMTP (IONOS-ready)** only when the state changes.
- Results are also written back into each JSON object under the key `"stormwarning"`, for later analysis together with weather data.

### 🤖 Classified Folder (for ML)
- JPG + JSON are additionally copied into  
  `jpg/classified/<classification>/`
- New subfolders are automatically created if not existing.
- Result: automatically organized training dataset (images + metadata).

---

## Project Structure

```
jpg/
 ├─ current/       → latest image (IMG_4903.jpg)
 ├─ old/           → archive of all images with timestamp
 ├─ classified/    → automatically sorted images & JSON by classification
json/              → JSON files matching each image
 ├─/stormwarning/storm_state.json → OK, WATCH, STORM 
modules/           → Python modules (capture, upload, openweathermap, classify, stormwarning)
main.py            → entry point
```

## Example Output (JSON)

```json
{
    "old_path": "jpg/old/IMG_4903_20250817_131645.jpg",
    "openweathermap": {
        "coord": { "lon": 11.1622, "lat": 49.4663 },
        "weather": [
            { "id": 803, "main": "Clouds", "description": "broken clouds", "icon": "04d" }
        ],
        "clouds": { "all": 75 },
        "wind": { "speed": 4.63, "deg": 310 }
    },
    "classification": "broken clouds",
    "classification_detail": {
        "coverage": "broken clouds",
        "phenomenon": null,
        "storm": false,
        "wind_speed_ms": 4.63,
        "clouds_percent": 75,
        "weather_id": 803
    },
    "stormwarning": {
        "prev_state": "OK",
        "new_state": "OK",
        "mailed": false,
        "wind_speed": 4.63,
        "wind_gust": null,
        "location": "Laufamholz",
        "state_file": "json/stormwarning/storm_state.json"
    }
}
```

---

## Sample Image (scattered clouds)

Here’s a sample capture from the Raspberry Pi webcam.  
The bottom of the image is blurred to protect my neighbours’ privacy.

![Webcam Sample](docs/webcam-sample.jpg)

---

## Installation & Usage

1. Clone or extract the project.  
2. Adjust configuration in `config.local.json` (OpenWeatherMap API key, upload settings, SMTP settings for stormwarning).  
3. Install dependencies:
   ```bash
   pip install requests
   ```
4. Install `sunwait` (required for daylight check):
   ```bash
   sudo apt-get install sunwait
   ```
5. Run the main script:
   ```bash
   python3 main.py
   ```

---

## License
This project is licensed under the [MIT License](LICENSE).

