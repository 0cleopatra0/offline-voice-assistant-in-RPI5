import pvporcupine
import pyaudio
import struct
import os
import time

ACCESS_KEY = "CnNEQfm996S877kY+Ml+GSSqdOb/IgW5CKVUSXzasBWK8+SRlwfeDg=="
KEYWORD_PATH = "Hey-Raspberry-Pi_en_raspberry-pi_v3_0_0.ppn"

# Create Porcupine instance
porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keyword_paths=[KEYWORD_PATH],
)

# Set up audio stream (Mic must support 16-bit, mono, 16kHz)
pa = pyaudio.PyAudio()
stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length
)

print("🎤 Say 'Hey Raspberry Pi' to activate assistant...")

try:
    while True:
        pcm_data = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm_data)

        # Print average loudness for debug
        avg_amplitude = sum(abs(x) for x in pcm) / len(pcm)
        print(f"🎧 Amplitude: {avg_amplitude:.2f}", end="\r")

        # Process for hotword detection
        keyword_index = porcupine.process(pcm)
        if keyword_index >= 0:
            print("\n🟢 Hotword Detected! Recording your question...")

            os.system("arecord -f cd -t wav -d 5 -r 16000 input.wav")

            os.system("./whisper.cpp/build/bin/whisper-cli -m ./whisper.cpp/models/ggml-tiny.en.bin -f input.wav > transcript.txt")

            with open("transcript.txt", "r") as f:
                lines = f.readlines()
                question = lines[-1].strip()

            print("🧠 You said:", question)

            print("🤖 Thinking...")
            response = os.popen(f"echo \"{question}\" | ollama run phi").read().strip()
            print("💬", response)

            os.system(f"espeak \"{response}\"")

            os.remove("input.wav")
            os.remove("transcript.txt")

except KeyboardInterrupt:
    print("\n❌ Exiting...")
finally:
    stream.stop_stream()
    stream.close()
    pa.terminate()
    porcupine.delete()
