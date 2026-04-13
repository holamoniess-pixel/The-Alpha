"""
Voice Control System - "Hey Google" style voice interface
Always-on voice control with wake word detection
"""

import asyncio
import numpy as np
import struct
import wave
from typing import Callable, Optional
import pyaudio
import winsound

class VoiceControlSystem:
    """
    Always-on voice control system
    Responds to wake word like "Hey Google"
    """
    
    def __init__(self, wake_word: str = "hey alpha", language: str = "en"):
        self.wake_word = wake_word
        self.language = language
        
        # Audio configuration
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        
        # Components
        self.wake_word_detector = None
        self.speech_recognizer = None
        self.tts_engine = None
        
        # State
        self.listening = False
        self.processing = False
        
        # Callback
        self.on_command: Optional[Callable] = None
    
    async def initialize(self):
        """Initialize voice components"""
        # Initialize wake word detector (lightweight)
        self.wake_word_detector = self.init_wake_word_detector()
        
        # Initialize speech recognizer (Whisper fallback)
        self.speech_recognizer = self.init_speech_recognizer()
        
        # Initialize TTS
        self.tts_engine = self.init_tts()
    
    def init_wake_word_detector(self):
        """Initialize lightweight wake word detection"""
        # Simple energy-based detector for now
        return SimpleWakeWordDetector(self.wake_word)
    
    def init_speech_recognizer(self):
        """Initialize speech recognition"""
        # Try to use Whisper if available
        try:
            import whisper
            model = whisper.load_model("base")  # Fast and accurate
            return model
        except ImportError:
            print("Whisper not available, using simple speech recognition")
            return SimpleSpeechRecognizer()
    
    def init_tts(self):
        """Initialize text-to-speech"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)  # Speed
            engine.setProperty('volume', 0.9)  # Volume
            return engine
        except ImportError:
            print("TTS not available, using fallback")
            return None
    
    async def start_listening(self):
        """Start continuous listening for wake word"""
        self.listening = True
        
        # Open audio stream
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        print(f"Listening for '{self.wake_word}'...")
        
        while self.listening:
            try:
                # Read audio chunk
                audio_data = stream.read(self.CHUNK, exception_on_overflow=False)
                
                # Check for wake word
                if self.detect_wake_word(audio_data):
                    print("Wake word detected!")
                    
                    # Play activation sound
                    self.play_activation_sound()
                    
                    # Listen for command
                    command = await self.listen_for_command(stream)
                    
                    if command:
                        print(f"Command: {command}")
                        
                        # Process command
                        if self.on_command:
                            response = await self.on_command(command)
                            
                            # Speak response
                            if response:
                                self.speak(response)
                
                await asyncio.sleep(0.01)  # Small delay
                
            except Exception as e:
                print(f"Error in voice loop: {e}")
        
        # Cleanup
        stream.stop_stream()
        stream.close()
        audio.terminate()
    
    def detect_wake_word(self, audio_data: bytes) -> bool:
        """Check if wake word is in audio"""
        try:
            # Convert bytes to int16
            pcm = struct.unpack_from("h" * (len(audio_data) // 2), audio_data)
            
            # Check with detector
            if hasattr(self.wake_word_detector, 'process'):
                result = self.wake_word_detector.process(pcm)
                return result >= 0
            else:
                # Fallback: energy-based
                return self.wake_word_detector.detect(pcm)
        except:
            return False
    
    async def listen_for_command(self, stream, timeout: float = 5.0) -> Optional[str]:
        """Listen for command after wake word"""
        print("Listening for command...")
        
        # Collect audio for timeout period
        frames = []
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                # Check if user stopped speaking
                if self.is_silence(data):
                    break
                
            except Exception as e:
                print(f"Error reading audio: {e}")
                break
        
        if not frames:
            return None
        
        # Convert to audio
        audio_data = b''.join(frames)
        
        # Convert to numpy array for speech recognition
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Transcribe with speech recognizer
        try:
            if hasattr(self.speech_recognizer, 'transcribe'):
                # Whisper
                result = self.speech_recognizer.transcribe(
                    audio_np,
                    language=self.language,
                    fp16=False
                )
                return result['text'].strip()
            else:
                # Simple recognizer
                return self.speech_recognizer.recognize(audio_np)
        except Exception as e:
            print(f"Transcription error: {e}")
            return None
    
    def is_silence(self, audio_data: bytes, threshold: int = 500) -> bool:
        """Check if audio is silence"""
        try:
            pcm = struct.unpack_from("h" * (len(audio_data) // 2), audio_data)
            rms = np.sqrt(np.mean(np.square(pcm)))
            return rms < threshold
        except:
            return False
    
    def play_activation_sound(self):
        """Play brief sound when activated"""
        try:
            winsound.Beep(1200, 100)  # 1200 Hz for 100ms
        except:
            pass
    
    def speak(self, text: str):
        """Convert text to speech"""
        if not self.tts_engine:
            return
        
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")
    
    async def stop(self):
        """Stop voice system"""
        self.listening = False


class SimpleWakeWordDetector:
    """Fallback wake word detector using simple energy matching"""
    
    def __init__(self, wake_word: str):
        self.wake_word = wake_word.lower()
        self.energy_history = []
        self.max_history = 10
    
    def detect(self, audio_pcm) -> bool:
        """Simple energy-based wake word detection"""
        # Calculate RMS energy
        energy = np.sqrt(np.mean(np.square(audio_pcm)))
        
        # Store energy history
        self.energy_history.append(energy)
        if len(self.energy_history) > self.max_history:
            self.energy_history.pop(0)
        
        # Simple threshold detection
        if len(self.energy_history) >= self.max_history:
            avg_energy = np.mean(self.energy_history[:-2])  # Exclude recent
            current_energy = self.energy_history[-1]
            
            # Trigger if current energy is significantly higher than average
            return current_energy > avg_energy * 2.0
        
        return False


class SimpleSpeechRecognizer:
    """Fallback speech recognizer using basic pattern matching"""
    
    def __init__(self):
        self.commands = {
            'open chrome': 'open_chrome',
            'open notepad': 'open_notepad',
            'close window': 'close_window',
            'minimize window': 'minimize_window',
            'what time': 'get_time',
            'type hello': 'type_hello',
            'click': 'click',
            'scroll down': 'scroll_down',
            'scroll up': 'scroll_up'
        }
    
    def recognize(self, audio_np) -> str:
        """Simple pattern-based recognition"""
        # This is a very basic fallback
        # In production, use proper speech recognition
        return "hello"  # Default response
