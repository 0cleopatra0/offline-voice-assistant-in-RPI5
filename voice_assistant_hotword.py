import pvporcupine
import pyaudio
import struct
import os
import time

# Init Porcupine for hotword "Hey Pico" (free)
porcupine = pvporcupine.create(keywords=["picovoice"])  # "picovoice" = free hotword

pa = pyaudio.PyAudio()
stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length
)

print("🎤 Say 'Hey Pi' to activate assistant...")

try:
    while True:
        pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

        if porcupine.process(pcm):
            print("🟢 Hotword Detected! Recording your question...")

            # Record 5 seconds audio
            os.system("arecord -f cd -t wav -d 5 -r 16000 input.wav")

            # Transcribe using whisper.cpp
            os.system("./whisper.cpp/main -m ./whisper.cpp/models/ggml-tiny.en.bin -f input.wav > transcript.txt")

            # Extract last line of transcript
            with open("transcript.txt", "r") as f:
                lines = f.readlines()
                question = lines[-1].strip()

            print("🧠 You said:", question)

            # Run Ollama model
            print("🤖 Thinking...")
            response = os.popen(f"echo \"{question}\" | ollama run phi").read()
            print("💬", response)

            # Speak the response
            os.system(f"espeak \"{response}\"")

            # Optional: Cleanup
            os.remove("input.wav")
            os.remove("transcript.txt")

except KeyboardInterrupt:
    print("❌ Exiting...")
finally:
    stream.stop_stream()
    stream.close()
    pa.terminate()
    porcupine.delete()
