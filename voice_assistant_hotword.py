import pvporcupine
import pyaudio
import struct
import wave
import subprocess
import time
from pathlib import Path
from collections import deque

# === CONFIGURATION ===
ACCESS_KEY    = "CnNEQfm996S877kY+Ml+GSSqdOb/IgW5CKVUSXzasBWK8+SRlwfeDg=="
KEYWORD_PATH  = "Hey-Raspberry-Pi_en_raspberry-pi_v3_0_0.ppn"
WHISPER_BIN   = "./whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "./whisper.cpp/models/ggml-tiny.en.bin"
OLLAMA_MODEL  = "phi"

# === AUDIO SETUP ===
def record_until_silence(pa, silence_duration=1.2, max_duration=10, silence_threshold=500):
    stream = pa.open(rate=16000, channels=1, format=pyaudio.paInt16,
                     input=True, frames_per_buffer=1024)
    frames = []
    silence = deque(maxlen=int(silence_duration * 16000 / 1024))
    start_time = time.time()

    print("🎙 Recording started. Speak now...")
    print("🔇 Recording will stop after silence or max duration.")

    while True:
        audio = stream.read(1024, exception_on_overflow=False)
        frames.append(audio)
        pcm = struct.unpack_from("h" * (len(audio) // 2), audio)
        silence.append(max(map(abs, pcm)) < silence_threshold)

        if all(silence) or (time.time() - start_time > max_duration):
            break

    stream.stop_stream()
    stream.close()

    path = Path("/tmp/query.wav")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))

    print(f"💾 Audio recorded to: {path}")
    return path

# === MAIN LOOP ===
def main():
    print("🔑 Initializing Porcupine...")
    porcupine = pvporcupine.create(
        access_key=ACCESS_KEY,
        keyword_paths=[KEYWORD_PATH]
    )

    pa = pyaudio.PyAudio()
    stream = pa.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16,
                     input=True, frames_per_buffer=porcupine.frame_length)

    print("🎤 Voice Assistant Ready!")
    print("🛑 Say: 'Hey Raspberry Pi' to activate...\n")

    try:
        while True:
            audio = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, audio)

            if porcupine.process(pcm) >= 0:
                print("🟢 Hotword Detected!")
                
                # Step 1: Record voice
                audio_path = record_until_silence(pa)

                # Step 2: Transcribe with Whisper
                print("📝 Transcribing using Whisper.cpp...")
                subprocess.run([
                    WHISPER_BIN,
                    "-m", WHISPER_MODEL,
                    "-f", str(audio_path),
                    "--language", "en",
                    "--output-txt"
                ], stdout=subprocess.DEVNULL)

                txt_path = audio_path.with_suffix(".txt")
                if not txt_path.exists():
                    print("❌ Whisper failed to transcribe.")
                    continue

                question = txt_path.read_text().strip().splitlines()[-1]
                print(f"🧠 Transcribed: \"{question}\"")

                # Step 3: Query local LLM
                print("🤖 Asking Ollama (phi)...")
                response = subprocess.check_output(
                    ["ollama", "run", OLLAMA_MODEL, question],
                    text=True
                ).strip()
                print(f"💬 Response: {response}")

                # Step 4: Speak response
                print("🔊 Speaking response using espeak...")
                subprocess.run(["espeak", response])

                # Step 5: Clean up
                print("🧹 Cleaning up temporary files...\n")
                audio_path.unlink(missing_ok=True)
                txt_path.unlink(missing_ok=True)

    except KeyboardInterrupt:
        print("\n👋 Assistant stopped by user.")

    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()

# === RUN ===
if __name__ == "__main__":
    print("🚀 Launching Raspberry Pi Voice Assistant...")
    main()
