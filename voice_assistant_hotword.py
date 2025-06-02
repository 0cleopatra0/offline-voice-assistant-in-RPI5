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
        self.wake_word = ""  # Will be set in setup_porcupine
        
        # Audio configuration
        self.sample_rate = 16000
        self.frame_length = 512
        
        # Environment-specific paths for Raspberry Pi
        self.whisper_path = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
        self.whisper_model = os.path.expanduser("~/whisper.cpp/models/ggml-tiny.en.bin")
        
        # Alternative paths if above don't exist
        if not os.path.exists(self.whisper_path):
            self.whisper_path = "../whisper.cpp/build/bin/whisper-cli"
        if not os.path.exists(self.whisper_model):
            self.whisper_model = "./whisper.cpp/models/ggml-tiny.en.bin"
        
        print("Initializing Voice Assistant for Raspberry Pi...")
        self.setup_porcupine()
        self.setup_audio()

    def setup_porcupine(self):
        """Initialize Porcupine hotword detection"""
        try:
            # Porcupine configuration
            ACCESS_KEY = "CnNEQfm996S877kY+Ml+GSSqdOb/IgW5CKVUSXzasBWK8+SRlwfeDg=="
            KEYWORD_PATH = "Hey-Raspberry-Pi_en_raspberry-pi_v3_0_0.ppn"
            
            # Check if custom keyword file exists
            if not os.path.exists(KEYWORD_PATH):
                print(f"Warning: Custom keyword file '{KEYWORD_PATH}' not found!")
                print("Please ensure the .ppn file is in the same directory as this script.")
                print("Using built-in 'computer' keyword as fallback...")
                
                # Fallback to built-in keyword
                self.porcupine = pvporcupine.create(
                    access_key=ACCESS_KEY,
                    keywords=['computer'],
                    sensitivities=[0.5]
                )
                self.wake_word = "computer"
            else:
                # Use custom "Hey Raspberry Pi" keyword
                self.porcupine = pvporcupine.create(
                    access_key=ACCESS_KEY,
                    keyword_paths=[KEYWORD_PATH],
                    sensitivities=[0.5]  # Adjust sensitivity (0.0 to 1.0)
                )
                self.wake_word = "Hey Raspberry Pi"
            
            print(f"Porcupine initialized successfully!")
            print(f"Wake word: '{self.wake_word}'")
            print(f"Frame length: {self.porcupine.frame_length}")
            print(f"Sample rate: {self.porcupine.sample_rate}")
            
        except Exception as e:
            print(f"Failed to initialize Porcupine: {e}")
            print("Common issues:")
            print("1. Invalid access key")
            print("2. Missing .ppn keyword file")
            print("3. Porcupine library not installed: pip3 install pvporcupine")
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
        print(f"\n🎤 Listening for wake word '{self.wake_word}'...")
        print(f"Say '{self.wake_word}' to activate the assistant")
        
        try:
            while self.is_running:
                pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                keyword_index = self.porcupine.process(pcm)
                
                if keyword_index >= 0:
                    print(f"\n🔊 Wake word '{self.wake_word}' detected! Listening for your question...")
                    self.handle_voice_command()
                    print(f"\n🎤 Listening for wake word '{self.wake_word}'...")
                    
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
        """Record audio command - Raspberry Pi optimized"""
        try:
            # Try multiple audio recording approaches for Raspberry Pi
            recording_commands = [
                # First try: default ALSA device
                ['arecord', '-D', 'default', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'wav', '-d', str(duration), filename],
                # Second try: plughw device
                ['arecord', '-D', 'plughw:1,0', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'wav', '-d', str(duration), filename],
                # Third try: hw device
                ['arecord', '-D', 'hw:1,0', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'wav', '-d', str(duration), filename]
            ]
            
            for cmd in recording_commands:
                try:
                    print(f"Trying recording with: {' '.join(cmd[:3])}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration+3)
                    
                    if result.returncode == 0 and os.path.exists(filename) and os.path.getsize(filename) > 1000:  # At least 1KB
                        print("✓ Recording successful")
                        return True
                    else:
                        print(f"Recording attempt failed: {result.stderr}")
                        continue
                        
                except subprocess.TimeoutExpired:
                    print("Recording timed out, trying next method...")
                    continue
                except Exception as e:
                    print(f"Recording error: {e}, trying next method...")
                    continue
            
            print("❌ All recording methods failed")
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
        print("🤖 RASPBERRY PI OFFLINE VOICE ASSISTANT")
        print("="*60)
        print(f"Wake word: '{self.wake_word}'")
        print("Press Ctrl+C to exit")
        print("Environment: Raspberry Pi optimized")
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
    """Main function with Raspberry Pi environment setup"""
    print("🍓 Raspberry Pi Voice Assistant Setup")
    print("="*50)
    
    # Environment checks for Raspberry Pi
    print("Checking Raspberry Pi environment...")
    
    # Check if running on Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' in cpuinfo:
                print("✓ Running on Raspberry Pi")
            else:
                print("⚠ Not detected as Raspberry Pi, but continuing...")
    except:
        print("⚠ Could not detect system type")
    
    # Check audio setup
    print("\nChecking audio devices...")
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Audio recording devices available")
            # Print available devices for debugging
            lines = result.stdout.split('\n')
            for line in lines:
                if 'card' in line.lower():
                    print(f"  {line.strip()}")
        else:
            print("❌ No audio recording devices found")
    except:
        print("❌ arecord not available")
    
    # Check dependencies
    dependencies = {
        'arecord': 'sudo apt install alsa-utils',
        'espeak': 'sudo apt install espeak', 
        'ollama': 'curl -fsSL https://ollama.com/install.sh | sh'
    }
    
    print("\nChecking dependencies...")
    missing_deps = []
    for cmd, install_cmd in dependencies.items():
        try:
            result = subprocess.run([cmd, '--help'], capture_output=True, timeout=5)
            if result.returncode == 0 or 'usage' in result.stderr.lower():
                print(f"✓ {cmd} available")
            else:
                missing_deps.append(f"{cmd}: {install_cmd}")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing_deps.append(f"{cmd}: {install_cmd}")
            print(f"❌ {cmd} not found")
    
    # Check Ollama service
    print("\nChecking Ollama...")
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=10)
        if 'phi' in result.stdout:
            print("✓ Ollama with Phi model ready")
        else:
            print("⚠ Phi model not found. Run: ollama pull phi")
    except Exception as e:
        print(f"❌ Ollama not ready: {e}")
        missing_deps.append("ollama: curl -fsSL https://ollama.com/install.sh | sh && ollama pull phi")
    
    # Check Whisper
    whisper_paths = [
        os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli"),
        "../whisper.cpp/build/bin/whisper-cli",
        "./whisper.cpp/build/bin/whisper-cli"
    ]
    
    whisper_found = False
    for path in whisper_paths:
        if os.path.exists(path):
            print(f"✓ Whisper found at: {path}")
            whisper_found = True
            break
    
    if not whisper_found:
        print("❌ Whisper not found. Build it with:")
        print("  git clone https://github.com/ggerganov/whisper.cpp")
        print("  cd whisper.cpp && make && ./models/download-ggml-model.sh tiny.en")
    
    # Check for .ppn file
    keyword_file = "Hey-Raspberry-Pi_en_raspberry-pi_v3_0_0.ppn"
    if os.path.exists(keyword_file):
        print(f"✓ Custom wake word file found: {keyword_file}")
    else:
        print(f"⚠ Custom wake word file not found: {keyword_file}")
        print("  Will use fallback 'computer' keyword")
    
    if missing_deps:
        print(f"\n❌ Missing dependencies detected:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install missing dependencies and try again.")
        return
    
    print(f"\n✓ Environment check complete!")
    print("="*50)
    
    # Set up audio environment for Raspberry Pi
    try:
        # Force audio output to 3.5mm jack (helpful for RPi)
        subprocess.run(['amixer', 'cset', 'numid=3', '1'], capture_output=True)
        print("Audio output set to 3.5mm jack")
    except:
        pass
    
    # Initialize and run the voice assistant
    try:
        assistant = VoiceAssistant()
        assistant.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nFatal error: {e}")
        print("Check the troubleshooting steps above.")

if __name__ == "__main__":
    main()
