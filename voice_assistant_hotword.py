import pvporcupine
import pyaudio
import wave
import subprocess

ACCESS_KEY = "CnNEQfm996S877kY+Ml+GSSqdOb/IgW5CKVUSXzasBWK8+SRlwfeDg=="
KEYWORD_PATH = "Hey-Raspberry-Pi_en_raspberry-pi_v3_0_0.ppn"

SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "recorded.wav"

def record_audio(filename=WAVE_OUTPUT_FILENAME, record_seconds=RECORD_SECONDS):
    print(f"Recording audio for {record_seconds} seconds...")
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE, input=True, frames_per_buffer=1024)
    frames = []
    for _ in range(0, int(SAMPLE_RATE / 1024 * record_seconds)):
        data = stream.read(1024)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    audio.terminate()
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    print("Recording complete.")

def transcribe_audio_with_whisper(audio_file=WAVE_OUTPUT_FILENAME):
    whisper_exe = "./whisper.cpp/main"
    model_path = "./whisper.cpp/models/ggml-tiny.en.bin"
    print("Transcribing audio offline with Whisper.cpp...")
    cmd = [whisper_exe, "-m", model_path, "-f", audio_file, "-otxt", "-nt", "1"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        transcription = result.stdout.strip() or result.stderr.strip()
        print(f"Transcription result: {transcription}")
        return transcription
    except Exception as e:
        print(f"Whisper.cpp transcription error: {e}")
        return ""

def query_ollama_llm(prompt_text):
    print(f"Sending prompt to Ollama LLM: {prompt_text}")
    cmd = ["ollama", "run", "phi", "--prompt", prompt_text]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        response = result.stdout.strip()
        print(f"Ollama response: {response}")
        return response
    except Exception as e:
        print(f"Ollama error: {e}")
        return "Sorry, I couldn't process your question."

def speak_text(text):
    print(f"Speaking response: {text}")
    subprocess.run(["espeak", text])

def main():
    print("Initializing Porcupine hotword detection...")
    porcupine = pvporcupine.create(access_key=ACCESS_KEY, keyword_paths=[KEYWORD_PATH])
    pa = pyaudio.PyAudio()
    audio_stream = pa.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=porcupine.frame_length)

    print("Listening for hotword 'Hey Pi'...")

    try:
        while True:
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_int16 = list(int.from_bytes(pcm[i:i+2], "little", signed=True) for i in range(0, len(pcm), 2))
            keyword_index = porcupine.process(pcm_int16)
            if keyword_index >= 0:
                print("\nHotword detected! Please ask your question after the beep.")
                # Optionally add beep sound here

                record_audio()
                question_text = transcribe_audio_with_whisper()

                if question_text:
                    answer_text = query_ollama_llm(question_text)
                    print(f"Assistant Answer: {answer_text}")
                    speak_text(answer_text)
                else:
                    print("Sorry, I didn't catch that. Please try again.")
                    speak_text("Sorry, I didn't catch that. Please try again.")

                print("\nListening for hotword 'Hey Pi' again...\n")

    except KeyboardInterrupt:
        print("Voice assistant stopped by user.")
    finally:
        audio_stream.stop_stream()
        audio_stream.close()
        pa.terminate()
        porcupine.delete()

if __name__ == "__main__":
    main()
