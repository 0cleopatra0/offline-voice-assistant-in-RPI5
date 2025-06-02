#!/usr/bin/env python3
import os
import sys
import struct
import pyaudio
import pvporcupine
import subprocess
import time
import signal
import threading
from queue import Queue

class VoiceAssistant:
    def __init__(self):
        self.porcupine = None
        self.pa = None
        self.audio_stream = None
        self.is_running = False
        
        # Audio configuration
        self.sample_rate = 16000
        self.frame_length = 512
        
        # Paths (adjust these according to your setup)
        self.whisper_path = "../whisper.cpp/build/bin/whisper-cli"
        self.whisper_model = "./whisper.cpp/models/ggml-tiny.en.bin"
        
        print("Initializing Voice Assistant...")
        self.setup_porcupine()
        self.setup_audio()

    def setup_porcupine(self):
        """Initialize Porcupine hotword detection"""
        try:
            # Initialize Porcupine with "Hey Pi" or use built-in keywords
            # You can use built-in keywords like 'picovoice', 'bumblebee', 'computer', etc.
            # Or create a custom "Hey Pi" keyword file
            
            self.porcupine = pvporcupine.create(
                access_key = "CnNEQfm996S877kY+Ml+GSSqdOb/IgW5CKVUSXzasBWK8+SRlwfeDg==", 
                porcupine = pvporcupine.create(access_key=access_key, keywords=["anjal"]),
                  # Using built-in keyword, change to custom if you have "Hey Pi"
                sensitivities=[0.5]  # Adjust sensitivity (0.0 to 1.0)
            )
            
            print(f"Porcupine initialized. Listening for wake word...")
            print(f"Frame length: {self.porcupine.frame_length}")
            print(f"Sample rate: {self.porcupine.sample_rate}")
            
        except Exception as e:
            print(f"Failed to initialize Porcupine: {e}")
            sys.exit(1)

    def setup_audio(self):
        """Initialize PyAudio"""
        try:
            self.pa = pyaudio.PyAudio()
            
            # Find the best audio input device
            device_index = self.find_audio_device()
            
            self.audio_stream = self.pa.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            print("Audio stream initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize audio: {e}")
            self.cleanup()
            sys.exit(1)

    def find_audio_device(self):
        """Find the best available audio input device"""
        print("Available audio devices:")
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  {i}: {info['name']} (inputs: {info['maxInputChannels']})")
        
        # Use default device
        return None

    def listen_for_hotword(self):
        """Listen continuously for the hotword"""
        print("\n🎤 Listening for wake word 'picovoice'...")
        print("Say 'picovoice' to activate the assistant")
        
        try:
            while self.is_running:
                pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                keyword_index = self.porcupine.process(pcm)
                
                if keyword_index >= 0:
                    print("\n🔊 Wake word detected! Listening for your question...")
                    self.handle_voice_command()
                    print("\n🎤 Listening for wake word 'picovoice'...")
                    
        except Exception as e:
            print(f"Error in hotword detection: {e}")

    def handle_voice_command(self):
        """Handle voice command after hotword detection"""
        try:
            # Record audio for the command
            print("Recording your question (5 seconds)...")
            audio_file = "command.wav"
            
            if self.record_command(audio_file, duration=5):
                # Transcribe the command
                transcription = self.transcribe_audio(audio_file)
                
                if transcription:
                    print(f"You said: {transcription}")
                    
                    # Process with LLM
                    response = self.get_llm_response(transcription)
                    
                    if response:
                        print(f"Assistant: {response}")
                        # Speak the response
                        self.speak_response(response)
                    else:
                        self.speak_response("I'm sorry, I couldn't process that.")
                else:
                    print("Could not understand the audio")
                    self.speak_response("I didn't catch that. Could you repeat?")
            
            # Cleanup
            if os.path.exists(audio_file):
                os.remove(audio_file)
                
        except Exception as e:
            print(f"Error handling voice command: {e}")

    def record_command(self, filename, duration=5):
        """Record audio command"""
        try:
            cmd = [
                'arecord',
                '-D', 'default',
                '-f', 'S16_LE',
                '-r', '16000',
                '-c', '1',
                '-t', 'wav',
                '-d', str(duration),
                filename
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration+2)
            
            if result.returncode == 0 and os.path.exists(filename) and os.path.getsize(filename) > 0:
                return True
            else:
                print(f"Recording failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Recording error: {e}")
            return False

    def transcribe_audio(self, audio_file):
        """Transcribe audio using Whisper"""
        try:
            if not os.path.exists(self.whisper_model):
                print(f"Whisper model not found at: {self.whisper_model}")
                return None
            
            cmd = [
                self.whisper_path,
                '-m', self.whisper_model,
                '-f', audio_file,
                '--output-txt',
                '--no-prints'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Read the transcription file
                txt_file = audio_file.replace('.wav', '.txt')
                if os.path.exists(txt_file):
                    with open(txt_file, 'r') as f:
                        transcription = f.read().strip()
                    os.remove(txt_file)  # Cleanup
                    return transcription if transcription else None
            
            print(f"Whisper error: {result.stderr}")
            return None
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

    def get_llm_response(self, question):
        """Get response from Ollama Phi model"""
        try:
            cmd = ['ollama', 'run', 'phi', question]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                response = result.stdout.strip()
                return response if response else None
            else:
                print(f"Ollama error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("Ollama response timed out")
            return None
        except Exception as e:
            print(f"LLM error: {e}")
            return None

    def speak_response(self, text):
        """Speak the response using espeak"""
        try:
            # Clean the text for better speech
            text = text.replace('\n', ' ').strip()
            if len(text) > 500:  # Limit response length
                text = text[:500] + "..."
            
            cmd = ['espeak', '-s', '150', '-v', 'en', text]
            subprocess.run(cmd, check=True, timeout=30)
            
        except Exception as e:
            print(f"TTS error: {e}")

    def cleanup(self):
        """Cleanup resources"""
        print("\nCleaning up...")
        
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        
        if self.pa:
            self.pa.terminate()
        
        if self.porcupine:
            self.porcupine.delete()

    def signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        print("\nShutting down voice assistant...")
        self.is_running = False
        self.cleanup()
        sys.exit(0)

    def run(self):
        """Main run loop"""
        print("="*60)
        print("🤖 OFFLINE VOICE ASSISTANT READY")
        print("="*60)
        print("Wake word: 'picovoice'")
        print("Press Ctrl+C to exit")
        print("="*60)
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.is_running = True
        
        try:
            self.listen_for_hotword()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

def main():
    """Main function"""
    # Check dependencies
    dependencies = {
        'arecord': 'sudo apt install alsa-utils',
        'espeak': 'sudo apt install espeak',
        'ollama': 'curl -fsSL https://ollama.com/install.sh | sh'
    }
    
    missing_deps = []
    for cmd, install_cmd in dependencies.items():
        try:
            subprocess.run([cmd, '--help'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_deps.append(f"{cmd}: {install_cmd}")
    
    if missing_deps:
        print("Missing dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install missing dependencies and try again.")
        return
    
    # Initialize and run the voice assistant
    assistant = VoiceAssistant()
    assistant.run()

if __name__ == "__main__":
    main()
