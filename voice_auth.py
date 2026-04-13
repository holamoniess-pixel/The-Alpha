import os
import sys
import json
import wave
import time
import logging
import hashlib
import numpy as np
from vosk import Model, SpkModel, KaldiRecognizer
import urllib.request
import zipfile

# Setup Logging
logging.basicConfig(filename='voice_auth.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

MODEL_PATH = "model-spk"
SPK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip"

class VoiceAuthenticator:
    def __init__(self, model_path=MODEL_PATH):
        self.model_path = model_path
        self.spk_model = None
        self.users_db = "users_voice_db.json"
        self.load_db()
        
        if not os.path.exists(self.model_path):
            logging.info("Speaker model not found. Downloading...")
            self.download_model()
            
        try:
            self.spk_model = SpkModel(self.model_path)
            logging.info("Speaker Model Loaded.")
            
            # Preload Grammar Model for Vector Extraction
            self.main_model_path = "model-small"
            if not os.path.exists(self.main_model_path):
                self.download_small_model(self.main_model_path)
            self.grammar_model = Model(self.main_model_path)
            logging.info("Grammar Model Loaded.")
            
        except Exception as e:
            logging.error(f"Failed to load models: {e}")

    def download_model(self):
        print("Downloading Speaker Model (This may take a moment)...")
        zip_path = "model-spk.zip"
        urllib.request.urlretrieve(SPK_MODEL_URL, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
        os.rename("vosk-model-spk-0.4", self.model_path)
        os.remove(zip_path)
        print("Model Downloaded and Extracted.")

    def load_db(self):
        if os.path.exists(self.users_db):
            with open(self.users_db, 'r') as f:
                self.users = json.load(f)
        else:
            self.users = {}

    def save_db(self):
        with open(self.users_db, 'w') as f:
            json.dump(self.users, f, indent=4)

    def extract_vector(self, audio_data):
        """
        Extract speaker vector from raw audio data (16kHz mono PCM).
        Using preloaded models.
        """
        if not self.grammar_model or not self.spk_model:
            logging.error("Models not loaded.")
            return None
            
        rec = KaldiRecognizer(self.grammar_model, 16000, self.spk_model)
        rec.AcceptWaveform(audio_data)
        res = json.loads(rec.FinalResult())
        
        if 'spk' in res:
            return res['spk']
        return None

    def download_small_model(self, path):
        print("Downloading Speech Model...")
        url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        zip_path = "model-small.zip"
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
        os.rename("vosk-model-small-en-us-0.15", path)
        os.remove(zip_path)

    def enroll_user(self, user_id, audio_file):
        """
        Enroll a user with an audio file (WAV 16kHz Mono).
        """
        wf = wave.open(audio_file, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            logging.error("Audio file must be WAV format mono PCM.")
            return False
            
        data = wf.readframes(wf.getnframes())
        vector = self.extract_vector(data)
        
        if vector:
            self.users[user_id] = {
                "vector": vector,
                "enrolled_at": time.time(),
                "hash": hashlib.sha256(json.dumps(vector).encode()).hexdigest()
            }
            self.save_db()
            logging.info(f"User {user_id} enrolled successfully.")
            return True
        else:
            logging.warning("Could not extract speaker vector.")
            return False

    def verify_user(self, audio_data, claimed_user="admin"):
        """
        Verify speaker against enrolled user.
        audio_data: Raw bytes
        """
        if claimed_user not in self.users:
            logging.warning(f"User {claimed_user} not found.")
            return False, 0.0
            
        vector = self.extract_vector(audio_data)
        if not vector:
            return False, 0.0
            
        enrolled_vector = self.users[claimed_user]['vector']
        
        # Cosine Similarity
        score = self.cosine_similarity(vector, enrolled_vector)
        logging.info(f"Verification Score: {score}")
        
        threshold = 0.65 # Tunable
        if score > threshold:
            return True, score
        return False, score

    def cosine_similarity(self, v1, v2):
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

if __name__ == "__main__":
    # Test
    auth = VoiceAuthenticator()
    # auth.enroll_user("admin", "test.wav")
