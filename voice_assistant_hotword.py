import pvporcupine
import pyaudio
import struct
import subprocess
import wave
import time
import os
from pathlib import Path

# === CONFIGURATION ===
ACCESS_KEY = "CnNEQfm996S877kY+Ml+GSSqdOb/IgW5CKVUSXzasBWK8+SRlwfeDg=="
KEYWORD_PATH = "Hey-Raspberry-Pi_en_raspberry-pi_v3_0_0.ppn"
WHISPER_BIN = "./whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "./whisper.cpp/models/ggml-tiny.en.bin"
OLLAMA_MODEL = "phi"

# === AUDIO RECORDING FUNCTION ===
def record_audio(output_path="input.wav", duration=5):
    print("🎙 Recording your question for 5 seconds...")
    os.system(f"arecord -f cd -t wav -d {duration} -r 16000 -c 1 {output_path}")
    if not Path(output_path).exists():
        print("❌ Failed to record audio.")
        return None
    print(f"💾 Saved recording to {output_path}")
    return output_path

# === MAIN FUNCTION ===
def main():
    print("🚀 Starting Raspberry Pi Voice Assistant...")
    print("🔑 Loading Porcupine hotword engine...")

    porcupine = pvporcupine.create(
        access_key=ACCESS_KEY,
        keyword_paths=[KEYWORD_PATH]
    )

    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )

    print("🎤 Say 'Hey Raspberry Pi' to activate...\n")

    try:
        while True:
            audio_data = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, audio_data)

            result = porcupine.process(pcm)
            if result >= 0:
                print("\n🟢 Hotword Detected!")

                # Step 1: Record
                wav_path = record_audio()
                if not wav_path:
                    continue

                # Step 2: Transcribe
                print("📝 Transcribing with Whisper.cpp...")
                subprocess.run([
                    WHISPER_BIN,
                    "-m", WHISPER_MODEL,
                    "-f", wav_path,
                    "--output-txt"
                ], stdout=subprocess.DEVNULL)

                transcript_path = Path("input.txt")
                if not transcript_path.exists():
                    print("❌ Transcription failed.")
                    continue

                question = transcript_path.read_text().strip().splitlines()[-1]
                print("🧠 You said:", question)

                # Step 3: Query LLM
                print("🤖 Thinking...")
                try:
                    response = subprocess.check_output(
                        ["ollama", "run", OLLAMA_MODEL, question],
                        text=True
                    ).strip()
                except subprocess.CalledProcessError:
                    print("❌ Ollama failed to generate response.")
                    continue

                print("💬", response)

                # Step 4: Speak
                print("🔊 Speaking response...")
                subprocess.run(["espeak", response])

                # Clean up
                Path(wav_path).unlink(missing_ok=True)
                transcript_path.unlink(missing_ok=True)
                print("✅ Done! Waiting for hotword...\n")

    except KeyboardInterrupt:
        print("\n🛑 Exiting...")

    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()

if __name__ == "__main__":
    main()
