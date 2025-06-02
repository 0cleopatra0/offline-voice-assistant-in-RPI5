import pvporcupine, pyaudio, struct, wave, subprocess, time
from pathlib import Path
from collections import deque

ACCESS_KEY   = "CnNEQfm996S877kY+Ml+GSSqdOb/IgW5CKVUSXzasBWK8+SRlwfeDg=="
KEYWORD_PATH = "Hey-Raspberry-Pi_en_raspberry-pi_v3_0_0.ppn"
WHISPER_BIN  = "./whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL= "./whisper.cpp/models/ggml-tiny.en.bin"
OLLAMA_MODEL = "phi"

def record_until_silence(pa, silence_secs=1.0, max_secs=10, threshold=500):
    stream = pa.open(rate=16000, channels=1, format=pyaudio.paInt16,
                     input=True, frames_per_buffer=1024)
    frames = []
    silence = deque(maxlen=int(silence_secs * 16000 / 1024))
    start = time.time()

    print("🎙 Recording. Speak your question...")

    while True:
        audio = stream.read(1024, exception_on_overflow=False)
        frames.append(audio)
        pcm = struct.unpack_from("h" * (len(audio) // 2), audio)
        silence.append(max(map(abs, pcm)) < threshold)

        if all(silence) or (time.time() - start > max_secs):
            break

    stream.stop_stream(); stream.close()

    path = Path("/tmp/query.wav")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))
    return path

# Initialize Porcupine
porcupine = pvporcupine.create(access_key=ACCESS_KEY, keyword_paths=[KEYWORD_PATH])
pa = pyaudio.PyAudio()
stream = pa.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16,
                 input=True, frames_per_buffer=porcupine.frame_length)

print("🎤 Say 'Hey Raspberry Pi' to activate...")

try:
    while True:
        audio = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, audio)

        if porcupine.process(pcm) >= 0:
            print("🟢 Hotword Detected!")

            # Record question
            audio_path = record_until_silence(pa)

            # Whisper transcription
            subprocess.run([
                WHISPER_BIN,
                "-m", WHISPER_MODEL,
                "-f", str(audio_path),
                "--language", "en",
                "--output-txt"
            ], stdout=subprocess.DEVNULL)

            text_file = audio_path.with_suffix(".txt")
            if text_file.exists():
                question = text_file.read_text().strip().splitlines()[-1]
                print("🧠 You said:", question)

                # Get LLM response
                print("🤖 Thinking...")
                result = subprocess.check_output(
                    ["ollama", "run", OLLAMA_MODEL, question], text=True
                ).strip()
                print("💬", result)

                # Speak response
                subprocess.run(["espeak", result])

                audio_path.unlink(missing_ok=True)
                text_file.unlink(missing_ok=True)
            else:
                print("⚠️ Whisper failed to transcribe.")

except KeyboardInterrupt:
    print("\n👋 Exiting...")

finally:
    stream.stop_stream()
    stream.close()
    pa.terminate()
    porcupine.delete()
