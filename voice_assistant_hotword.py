import pvporcupine
import pyaudio
import struct
import os
import time

# Initialize Porcupine with your offline keyword (.ppn file)
porcupine = pvporcupine.create(
    access_key='CnNEQfm996S877kY+Ml+GSSqdOb/IgW5CKVUSXzasBWK8+SRlwfeDg==',
    keyword_paths=['Hey-Raspberry-Pi_en_raspberry-pi_v3_0_0.ppn']
)

# Setup microphone input stream
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
        # Read audio frames from mic
        pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

        # Hotword detection
        if porcupine.process(pcm):
            print("🟢 Hotword Detected! Recording your question...")

            # Record audio for 5 seconds
            os.system("arecord -f cd -t wav -d 5 -r 16000 input.wav")

            # Transcribe with whisper.cpp
            os.system("./whisper.cpp/build/bin/whisper-cli -m ./whisper.cpp/models/ggml-tiny.en.bin -f input.wav > transcript.txt")

            # Read last line as the question
            with open("transcript.txt", "r") as f:
                lines = f.readlines()
                question = lines[-1].strip()

            print("🧠 You said:", question)

            # Generate response using Ollama + Phi model
            print("🤖 Thinking...")
            response = os.popen(f"echo \"{question}\" | ollama run phi").read().strip()
            print("💬", response)

            # Speak response
            os.system(f"espeak \"{response}\"")

            # Cleanup
            os.remove("input.wav")
            os.remove("transcript.txt")

except KeyboardInterrupt:
    print("❌ Exiting...")
finally:
    stream.stop_stream()
    stream.close()
    pa.terminate()
    porcupine.delete()
