import pvporcupine
import pyaudio
import struct
import os
import time

# Your Porcupine access key and keyword file
ACCESS_KEY = "CnNEQfm996S877kY+Ml+GSSqdOb/IgW5CKVUSXzasBWK8+SRlwfeDg=="
KEYWORD_PATH = "Hey-Raspberry-Pi_en_raspberry-pi_v3_0_0.ppn"

# Replace these with your actual device indexes found from step 3
INPUT_DEVICE_INDEX = 2   # USB Mic input device index
OUTPUT_DEVICE_INDEX = 2  # USB Speaker output device index (usually same as mic if USB combo device)

print("🚀 Starting Raspberry Pi Voice Assistant...")
print("🔑 Loading Porcupine hotword engine...")

# Initialize Porcupine
porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keyword_paths=[KEYWORD_PATH],
)

# Initialize PyAudio
pa = pyaudio.PyAudio()

print(f"🎤 Opening audio input device index {INPUT_DEVICE_INDEX} for hotword detection...")

stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    input_device_index=INPUT_DEVICE_INDEX,
    frames_per_buffer=porcupine.frame_length
)

print("🎤 Say 'Hey Raspberry Pi' to activate assistant...")

try:
    while True:
        pcm_data = stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm_data)

        # Optionally print audio amplitude to check mic input level
        avg_amplitude = sum(abs(x) for x in pcm) / len(pcm)
        print(f"🎧 Listening... Audio amplitude: {avg_amplitude:.2f}", end="\r")

        # Detect hotword
        keyword_index = porcupine.process(pcm)
        if keyword_index >= 0:
            print("\n🟢 Hotword Detected! Recording your question for 5 seconds...")

            # Record audio using arecord from correct device
            record_cmd = f"arecord -D hw:{INPUT_DEVICE_INDEX},0 -f cd -d 5 -r 16000 input.wav"
            print(f"🎙️ Running command to record: {record_cmd}")
            os.system(record_cmd)

            print("📄 Transcribing audio with Whisper...")
            whisper_cmd = "./whisper.cpp/build/bin/whisper-cli -m ./whisper.cpp/models/ggml-tiny.en.bin -f input.wav > transcript.txt"
            print(f"🖥️ Running command: {whisper_cmd}")
            os.system(whisper_cmd)

            with open("transcript.txt", "r") as f:
                lines = f.readlines()
                if lines:
                    question = lines[-1].strip()
                else:
                    question = ""

            if question:
                print(f"🧠 You said: {question}")
                print("🤖 Thinking... Generating response with Ollama...")
                response = os.popen(f"echo \"{question}\" | ollama run phi").read().strip()
                print(f"💬 Response: {response}")

                # Use espeak to speak the response (send output to USB speaker)
                # By default espeak uses system default audio output, which we set in .asoundrc
                speak_cmd = f'espeak "{response}"'
                print(f"🔊 Speaking response with command: {speak_cmd}")
                os.system(speak_cmd)
            else:
                print("⚠️ Could not transcribe the audio. Please try again.")

            # Clean up files
            os.remove("input.wav")
            os.remove("transcript.txt")

            print("\n🎤 Say 'Hey Raspberry Pi' to activate assistant again...")

except KeyboardInterrupt:
    print("\n❌ Exiting...")

finally:
    stream.stop_stream()
    stream.close()
    pa.terminate()
    porcupine.delete()
