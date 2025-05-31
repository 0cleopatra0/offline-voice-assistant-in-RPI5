Offline-Voice-Assistant-in-Raspberry PI 5(8GB)
Enable seamless hands-free voice interaction on Raspberry Pi by using audio input and output.

Project Overview

This project sets up a fully offline voice assistant on a Raspberry Pi 5 (8GB) with the following features:

- Hotword Detection: Listens for the phrase "Hey Pi" using Porcupine.
- Speech-to-Text: Converts voice input to text using Whisper.cpp.
- LLM Response: Processes the text with Ollama’s Phi language model.
- Text-to-Speech: Speaks the response using Espeak.
- Audio I/O Support: Works with TRRS earphones or USB headset for both mic and speaker.
- Fully Offline: No internet required after initial model setup.


Prerequisites

Hardware
- Raspberry Pi 5 (8GB recommended)  
- Microphone (built-in on USB headset or TRRS 3.5mm earphones)  
- Speaker or earphones for audio output  
- SD Card (32GB+ recommended)  
- Official Raspberry Pi Power Supply  

Operating System  
- Ubuntu 24.04 LTS (64-bit) or Raspberry Pi OS Bookworm (64-bit)

---

Setup Instructions
1. System Update and Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
```

# Install audio tools and dependencies
```bash
sudo apt install -y alsa-utils espeak portaudio19-dev python3-pyaudio ffmpeg
```

# Build essentials for whisper.cpp
```bash
sudo apt install -y build-essential cmake libfftw3-dev libopenblas-dev
```

# Install Python packages for hotword detection
```bash
pip3 install pvporcupine pyaudio
```

2. Clone and Build Whisper.cpp
```bash
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make
./models/download-ggml-model.sh tiny.en
cd ..
```

3. Install Ollama and Download Model
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi
```

4. Test Audio Input and Output
   List recording devices:
   ```bash
   arecord -l
   ```
   List playback devices:
   ```bash
   aplay -l
   ```
   Record a 5-second audio sample and play it back:
   ```bash
   arecord -d 5 test.wav
   aplay test.wav
   ```
   Use alsamixer to adjust microphone and output volumes:
    ```bash
   alsamixer
   ```
   Force audio output to 3.5mm jack (if needed)
   ```bash
   amixer cset numid=3 1
   ```
5. Add Your Voice Assistant Python Script
Create a Python script (e.g., voice_assistant_hotword.py) with the hotword detection, speech-to-text, LLM query, and text-to-speech logic.
(Full script code provided separately)

6. Run Your Voice Assistant
```bash
   python3 voice_assistant_hotword.py
```

Optional: Auto-run on Startup
Make your script executable:
```bash
chmod +x voice_assistant_hotword.py
```
Add to crontab for auto-start on reboot:
```bash
crontab -e
```
Add this line at the end:
```bash
@reboot /usr/bin/python3 /home/pi/voice_assistant_hotword.py &
```
   
