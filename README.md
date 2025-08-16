# raspberry-cam

A Raspberry Pi project for capturing webcam images and storing them with a modular **Python + Bash** pipeline.  
Designed for robustness, automation, and integration into IoT workflows.

## Features
- Capture images from a USB webcam using Bash and Python  
- Modular script structure (separation of capture, processing, and upload)  
- Configurable via `config.local.json` (not part of the repository)  
- Automatic storage of images in `jpg/`  
- Easily extensible for weather monitoring, time-lapse, or IoT use cases  

## Requirements
- Raspberry Pi (tested on Raspberry Pi 4)  
- USB webcam  
- Python 3.11+  
- Bash  
- `fswebcam` installed (`sudo apt install fswebcam`)  

## Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/eddy-san/raspberry-cam.git
   cd raspberry-cam
   ```
2. Install dependencies:
   ```bash
   sudo apt update && sudo apt install fswebcam python3
   ```
3. Create your local config file:
   ```bash
   cp config.local.json.example config.local.json
   ```
   (Edit with your custom settings.)

4. Run the main script:
   ```bash
   python3 main.py
   ```

## Project Structure
```
.
├── config.local.json    # Local config (ignored by git)
├── jpg/                 # Captured images
├── main.py              # Main entry point
├── modules/             # Python modules (capture, upload, etc.)
└── .gitignore
```

## License
This project is licensed under the [MIT License](LICENSE).
