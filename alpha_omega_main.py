#!/usr/bin/env python3
"""
ALPHA AND OMEGA - MASTER SYSTEM
Version: 1.1.0
Voice-Activated PC Control System (Hey Google Style)
Production Implementation Ready
"""

import asyncio
import logging
import yaml
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import speech_recognition as sr
import pyttsx3
import pyautogui
import cv2
import numpy as np
from PIL import Image
import psutil
import sqlite3
import hashlib
import os
import subprocess
import webbrowser
import requests
from dataclasses import dataclass
from enum import Enum
import wave
import pyaudio

# Import system components
from voice_system import VoiceControlSystem
from intelligence_engine import IntelligenceEngine
from learning_engine import LearningEngine
from memory_system import MemorySystem
from automation_engine import AutomationEngine
from automation import AutomationEngine as AdvancedAutomationEngine
from security_framework import SecurityFramework
from performance_optimizer import PerformanceOptimizer

# System Constants
VERSION = "1.1.0"
WAKE_WORD = "hey alpha"
SYSTEM_NAME = "AlphaOmega"
CONFIG_FILE = "config.yaml"
DATABASE_FILE = "alpha_omega.db"
LOGS_DIR = "logs"
MEMORY_DIR = "memory"

class SystemState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    LEARNING = "learning"
    AUTOMATING = "automating"

@dataclass
class CommandResult:
    success: bool
    message: str
    data: Optional[Dict] = None

class AlphaOmegaSystem:
    """
    Main system class - orchestrates all components
    """
    
    def __init__(self, config_path: str = CONFIG_FILE):
        self.version = VERSION
        self.config = self.load_config(config_path)
        self.state = SystemState.IDLE
        self.running = False
        self.initialized = False
        
        # Core components
        self.voice_system = None
        self.intelligence_engine = None
        self.learning_system = None
        self.memory_system = None
        self.automation_engine = None
        self.security_framework = None
        self.performance_optimizer = None
        
        # System metrics
        self.start_time = datetime.now()
        self.command_count = 0
        self.error_count = 0
        self.learning_iterations = 0
        
        # Initialize logging
        self.setup_logging()
        self.logger.info("Alpha Omega System Initializing...")
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load system configuration with intelligent defaults"""
        default_config = {
            'system': {
                'name': SYSTEM_NAME,
                'version': VERSION,
                'wake_word': WAKE_WORD,
                'language': 'en-US',
                'max_memory_mb': 2048,
                'learning_enabled': True,
                'auto_start': True,
                'offline_mode': True
            },
            'voice': {
                'engine': 'whisper-base',
                'sample_rate': 16000,
                'chunk_size': 1024,
                'timeout': 5,
                'sensitivity': 0.5,
                'noise_reduction': True
            },
            'intelligence': {
                'llm_model': 'llama-7b-q4',
                'context_window': 4096,
                'temperature': 0.7,
                'max_tokens': 512,
                'reasoning_enabled': True
            },
            'learning': {
                'pattern_recognition': True,
                'behavior_analysis': True,
                'prediction_enabled': True,
                'adaptation_rate': 0.1,
                'memory_retention_days': 30
            },
            'automation': {
                'gui_automation': True,
                'system_commands': True,
                'web_automation': True,
                'file_operations': True,
                'safety_mode': True
            },
            'security': {
                'voice_auth': True,
                'command_whitelist': True,
                'activity_logging': True,
                'threat_detection': True,
                'encryption_enabled': True
            },
            'performance': {
                'cpu_limit': 80,
                'memory_limit': 85,
                'response_time_ms': 500,
                'cache_size_mb': 512,
                'optimization_level': 'high'
            },
            'gaming': {
                'game_detection': True,
                'performance_mode': True,
                'macro_support': True,
                'voice_commands': True,
                'auto_optimization': True
            }
        }
        
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f) or {}
                    self._deep_merge(default_config, user_config)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                
        return default_config
    
    def _deep_merge(self, base: Dict, update: Dict) -> None:
        """Deep merge configuration dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def setup_logging(self):
        """Configure comprehensive logging system"""
        # Create logs directory
        Path(LOGS_DIR).mkdir(exist_ok=True)
        
        # Configure logging
        log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        log_file = Path(LOGS_DIR) / f"alpha_omega_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(),
                logging.handlers.RotatingFileHandler(
                    log_file, maxBytes=10*1024*1024, backupCount=5
                )
            ]
        )
        
        self.logger = logging.getLogger('AlphaOmega')
        self.logger.info("Logging system initialized")
    
    async def initialize(self):
        """Initialize all system components with error handling"""
        self.logger.info("Starting Alpha Omega initialization...")
        
        try:
            # 1. Initialize memory system first (needed by others)
            self.logger.info("Initializing memory system...")
            self.memory_system = MemorySystem(self.config['learning'])
            await self.memory_system.initialize()
            
            # 2. Initialize voice system
            self.logger.info("Initializing voice system...")
            self.voice_system = VoiceControlSystem(
                self.config['voice'], 
                self.config['system']['wake_word']
            )
            await self.voice_system.initialize()
            
            # 3. Initialize intelligence engine
            self.logger.info("Loading AI intelligence engine...")
            self.intelligence_engine = IntelligenceEngine(
                self.config['intelligence'],
                self.memory_system
            )
            await self.intelligence_engine.initialize()
            
            # 4. Initialize learning system
            if self.config['system']['learning_enabled']:
                self.logger.info("Initializing learning system...")
                self.learning_system = LearningSystem(
                    self.config['learning'],
                    self.memory_system
                )
                await self.learning_system.initialize()
            
            # 5. Initialize automation engine
            self.logger.info("Initializing automation engine...")
            self.automation_engine = AdvancedAutomationEngine(
                self.config['automation']
            )
            await self.automation_engine.initialize()
            
            # 6. Initialize security framework
            self.logger.info("Initializing security framework...")
            self.security_framework = SecurityFramework(
                self.config['security']
            )
            await self.security_framework.initialize()
            
            # 7. Initialize performance optimizer
            self.logger.info("Initializing performance optimizer...")
            self.performance_optimizer = PerformanceOptimizer(
                self.config['performance']
            )
            
            # 8. Connect all components
            self._connect_components()
            
            self.initialized = True
            self.logger.info("System initialized successfully")
            
            # Play initialization sound
            await self._play_ready_sound()
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise RuntimeError(f"System initialization failed: {e}")
    
    def _connect_components(self):
        """Wire up component communication channels"""
        # Voice → Intelligence → Automation pipeline
        self.voice_system.set_command_handler(self._process_voice_command)
        
        # Intelligence → Memory
        self.intelligence_engine.set_memory_system(self.memory_system)
        
        # Learning → All systems
        if self.learning_system:
            self.learning_system.connect_to_voice(self.voice_system)
            self.learning_system.connect_to_automation(self.automation_engine)
            self.learning_system.connect_to_intelligence(self.intelligence_engine)
        
        # Security monitoring
        self.security_framework.monitor_system(self)
        
        # Performance monitoring
        self.performance_optimizer.monitor_components({
            'voice': self.voice_system,
            'intelligence': self.intelligence_engine,
            'automation': self.automation_engine,
            'memory': self.memory_system
        })
    
    async def _process_voice_command(self, command: str) -> str:
        """Process voice commands through the intelligence pipeline"""
        self.command_count += 1
        self.state = SystemState.PROCESSING
        
        try:
            # Security check
            if not self.security_framework.is_command_allowed(command):
                return "Command blocked by security policy"
            
            # Learning system analysis
            if self.learning_system:
                self.learning_system.record_command(command)
            
            # Intelligence processing
            intent = await self.intelligence_engine.process_command(command)
            
            # Execute based on intent
            if intent['type'] == 'automation':
                # Use the advanced automation engine
                result = await self.automation_engine.execute_command(
                    intent.get('command', ''), 
                    intent.get('parameters', {})
                )
                # Convert AutomationResult to CommandResult
                result = CommandResult(result.success, result.message, result.data)
            elif intent['type'] == 'query':
                result = await self.intelligence_engine.answer_query(intent)
            elif intent['type'] == 'system':
                result = await self._handle_system_command(intent)
            else:
                result = CommandResult(False, "Unknown command type")
            
            # Learning from result
            if self.learning_system and result.success:
                self.learning_system.learn_from_result(command, result)
            
            return result.message
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Command processing error: {e}")
            return f"Error processing command: {str(e)}"
        finally:
            self.state = SystemState.IDLE
    
    async def _handle_system_command(self, intent: Dict) -> CommandResult:
        """Handle system-level commands"""
        command = intent.get('command', '')
        
        if command == 'status':
            return CommandResult(True, self.get_system_status())
        elif command == 'help':
            return CommandResult(True, self.get_help_text())
        elif command == 'restart':
            await self.restart()
            return CommandResult(True, "System restarting...")
        elif command == 'shutdown':
            await self.stop()
            return CommandResult(True, "System shutting down...")
        else:
            return CommandResult(False, f"Unknown system command: {command}")
    
    async def start(self):
        """Start the Alpha Omega system"""
        if not self.initialized:
            await self.initialize()
        
        self.running = True
        self.start_time = datetime.now()
        self.logger.info("Alpha Omega system starting...")
        
        # Start all components concurrently
        tasks = []
        
        # Core system tasks
        tasks.append(self.voice_system.start_listening())
        tasks.append(self.memory_system.start_maintenance())
        
        # Optional components
        if self.learning_system:
            tasks.append(self.learning_system.start_learning())
        
        if self.performance_optimizer:
            tasks.append(self.performance_optimizer.start_monitoring())
        
        # Start security monitoring
        tasks.append(self.security_framework.start_monitoring())
        
        # Run all tasks
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info("Alpha Omega system is now running")
        await self._announce_status("System online and ready")
    
    async def stop(self):
        """Gracefully shut down the system"""
        self.logger.info("Initiating system shutdown...")
        self.running = False
        
        # Stop all components
        shutdown_tasks = []
        
        if self.voice_system:
            shutdown_tasks.append(self.voice_system.stop())
        
        if self.learning_system:
            shutdown_tasks.append(self.learning_system.stop())
        
        if self.memory_system:
            shutdown_tasks.append(self.memory_system.save_and_close())
        
        if self.security_framework:
            shutdown_tasks.append(self.security_framework.stop())
        
        if self.performance_optimizer:
            shutdown_tasks.append(self.performance_optimizer.stop())
        
        # Wait for all components to stop
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        self.logger.info("System shutdown complete")
    
    async def restart(self):
        """Restart the system"""
        await self.stop()
        await asyncio.sleep(1)
        await self.start()
    
    def get_system_status(self) -> str:
        """Get comprehensive system status"""
        uptime = datetime.now() - self.start_time
        
        status = f"""
Alpha Omega System Status:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
System: {self.config['system']['name']} v{self.version}
State: {self.state.value}
Uptime: {str(uptime).split('.')[0]}
Commands Processed: {self.command_count}
Learning Iterations: {self.learning_iterations}
Error Count: {self.error_count}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Component Status:
"""
        
        # Add component-specific status
        if self.voice_system:
            status += f"Voice System: {'Active' if self.voice_system.is_listening() else 'Inactive'}\n"
        
        if self.memory_system:
            status += f"Memory System: {self.memory_system.get_usage()}\n"
        
        if self.learning_system:
            status += f"Learning System: {'Active' if self.learning_system.is_learning() else 'Inactive'}\n"
        
        if self.security_framework:
            status += f"Security Status: {self.security_framework.get_status()}\n"
        
        # System resources
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        
        status += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
System Resources:
CPU Usage: {cpu_percent}%
Memory Usage: {memory_percent}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        return status.strip()
    
    def get_help_text(self) -> str:
        """Get help information"""
        return f"""
Alpha Omega Help System:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Voice Commands:
• "{WAKE_WORD}" - Activate system
• "Hey Alpha, what can you do?" - Show capabilities
• "Hey Alpha, system status" - Get system info
• "Hey Alpha, help" - Show this help

System Commands:
• Automation tasks (open apps, control windows)
• System queries (status, performance)
• Learning mode (analyze patterns, suggest improvements)
• Security features (monitoring, protection)

Try saying: "Hey Alpha, open calculator"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".strip()
    
    async def _play_ready_sound(self):
        """Play system ready sound"""
        try:
            # Simple beep for now - can be replaced with actual sound file
            print("\a")  # System bell
        except:
            pass
    
    async def _announce_status(self, message: str):
        """Announce system status via voice"""
        try:
            if self.voice_system and self.voice_system.tts_engine:
                await self.voice_system.speak(message)
        except:
            pass


# Component Classes (to be implemented in separate files)
class VoiceControlSystem:
    """Advanced voice control with wake word detection"""
    
    def __init__(self, config: Dict, wake_word: str):
        self.config = config
        self.wake_word = wake_word.lower()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone(sample_rate=config['sample_rate'])
        self.tts_engine = None
        self.is_listening = False
        self.command_handler = None
        self.logger = logging.getLogger('VoiceSystem')
        
    async def initialize(self):
        """Initialize voice recognition and synthesis"""
        # Configure speech recognition
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        # Initialize TTS engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 180)
        self.tts_engine.setProperty('volume', 0.9)
        
        # Calibrate microphone
        with self.microphone as source:
            self.logger.info("Calibrating microphone...")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            
        self.logger.info("Voice system initialized")
    
    def set_command_handler(self, handler: Callable):
        """Set the command processing handler"""
        self.command_handler = handler
    
    async def start_listening(self):
        """Start continuous voice listening"""
        self.is_listening = True
        self.logger.info("Starting voice recognition...")
        
        while self.is_listening:
            try:
                with self.microphone as source:
                    self.logger.debug("Listening for wake word...")
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                    
                # Process audio
                await self._process_audio(audio)
                
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Voice recognition error: {e}")
                await asyncio.sleep(1)
    
    async def _process_audio(self, audio):
        """Process captured audio"""
        try:
            # Recognize speech
            text = self.recognizer.recognize_google(audio, language=self.config['language'])
            text = text.lower()
            
            self.logger.info(f"Heard: {text}")
            
            # Check for wake word
            if self.wake_word in text:
                # Remove wake word and process command
                command = text.replace(self.wake_word, '').strip()
                
                if command and self.command_handler:
                    self.logger.info(f"Processing command: {command}")
                    response = await self.command_handler(command)
                    await self.speak(response)
                    
        except sr.UnknownValueError:
            pass  # Ignore unknown speech
        except sr.RequestError as e:
            self.logger.error(f"Speech recognition service error: {e}")
            await self.speak("Speech recognition service is unavailable")
    
    async def speak(self, text: str):
        """Text-to-speech output"""
        if self.tts_engine and text:
            self.logger.info(f"Speaking: {text}")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
    
    def is_listening(self) -> bool:
        """Check if voice system is active"""
        return self.is_listening
    
    async def stop(self):
        """Stop voice recognition"""
        self.is_listening = False
        self.logger.info("Voice system stopped")


class MemorySystem:
    """Advanced memory system with unlimited storage"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.db_path = Path(MEMORY_DIR) / DATABASE_FILE
        self.connection = None
        self.cache = {}
        self.logger = logging.getLogger('MemorySystem')
        
    async def initialize(self):
        """Initialize memory database and structures"""
        Path(MEMORY_DIR).mkdir(exist_ok=True)
        
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.execute('PRAGMA journal_mode=WAL')
        
        # Create memory tables
        self._create_tables()
        
        # Initialize cache
        self._initialize_cache()
        
        self.logger.info("Memory system initialized")
    
    def _create_tables(self):
        """Create database tables for different memory types"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                command TEXT NOT NULL,
                intent TEXT,
                success BOOLEAN,
                response TEXT,
                context TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 0.0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_behavior (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                behavior_type TEXT NOT NULL,
                behavior_data TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                context TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                severity TEXT DEFAULT 'info'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 1.0
            )
            """
        ]
        
        for table_sql in tables:
            self.connection.execute(table_sql)
        
        self.connection.commit()
    
    def _initialize_cache(self):
        """Initialize memory cache"""
        # Load recent patterns
        cursor = self.connection.execute(
            "SELECT * FROM patterns WHERE last_seen > datetime('now', '-1 day')"
        )
        for row in cursor:
            self.cache[f"pattern_{row[0]}"] = dict(zip([d[0] for d in cursor.description], row))
    
    async def store_command(self, command: str, intent: str, success: bool, response: str, context: Dict = None):
        """Store command execution data"""
        self.connection.execute(
            """INSERT INTO commands (command, intent, success, response, context)
               VALUES (?, ?, ?, ?, ?)""",
            (command, intent, success, response, json.dumps(context) if context else None)
        )
        self.connection.commit()
    
    async def store_pattern(self, pattern_type: str, pattern_data: Dict, confidence: float = 1.0):
        """Store learned patterns"""
        pattern_json = json.dumps(pattern_data)
        
        # Check if pattern exists
        cursor = self.connection.execute(
            "SELECT id, frequency FROM patterns WHERE pattern_type = ? AND pattern_data = ?",
            (pattern_type, pattern_json)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing pattern
            self.connection.execute(
                """UPDATE patterns SET frequency = frequency + 1, last_seen = CURRENT_TIMESTAMP, confidence = ?
                   WHERE id = ?""",
                (confidence, existing[0])
            )
        else:
            # Insert new pattern
            self.connection.execute(
                """INSERT INTO patterns (pattern_type, pattern_data, confidence)
                   VALUES (?, ?, ?)""",
                (pattern_type, pattern_json, confidence)
            )
        
        self.connection.commit()
    
    async def get_patterns(self, pattern_type: str = None, limit: int = 100) -> List[Dict]:
        """Retrieve learned patterns"""
        query = "SELECT * FROM patterns"
        params = []
        
        if pattern_type:
            query += " WHERE pattern_type = ?"
            params.append(pattern_type)
        
        query += " ORDER BY frequency DESC, confidence DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.connection.execute(query, params)
        patterns = []
        
        for row in cursor:
            pattern = {
                'id': row[0],
                'type': row[1],
                'data': json.loads(row[2]),
                'frequency': row[3],
                'last_seen': row[4],
                'confidence': row[5]
            }
            patterns.append(pattern)
        
        return patterns
    
    async def start_maintenance(self):
        """Start memory maintenance tasks"""
        while True:
            try:
                # Clean old data
                retention_days = self.config['memory_retention_days']
                
                self.connection.execute(
                    "DELETE FROM commands WHERE timestamp < datetime('now', '-{} days')".format(retention_days)
                )
                
                self.connection.execute(
                    "DELETE FROM system_events WHERE timestamp < datetime('now', '-7 days')"
                )
                
                self.connection.commit()
                
                # Vacuum database
                self.connection.execute("VACUUM")
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                self.logger.error(f"Memory maintenance error: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes
    
    def get_usage(self) -> str:
        """Get memory usage statistics"""
        cursor = self.connection.execute("SELECT COUNT(*) FROM commands")
        command_count = cursor.fetchone()[0]
        
        cursor = self.connection.execute("SELECT COUNT(*) FROM patterns")
        pattern_count = cursor.fetchone()[0]
        
        cursor = self.connection.execute("SELECT COUNT(*) FROM knowledge_base")
        knowledge_count = cursor.fetchone()[0]
        
        return f"Commands: {command_count}, Patterns: {pattern_count}, Knowledge: {knowledge_count}"
    
    async def save_and_close(self):
        """Save memory and close database"""
        if self.connection:
            self.connection.commit()
            self.connection.close()
            self.logger.info("Memory system saved and closed")


# Additional component classes would be implemented in separate files
# For brevity, showing the main system structure

# Main entry point
async def main():
    """Main entry point for Alpha Omega system"""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    ALPHA OMEGA SYSTEM                      ║
║                 Version {VERSION} - Production Ready            ║
║                                                              ║
║    Voice-Activated PC Control System (Hey Google Style)     ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    system = AlphaOmegaSystem()
    
    try:
        await system.initialize()
        await system.start()
        
        # Keep system running
        while system.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutdown signal received...")
        await system.stop()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        await system.stop()
        
    finally:
        print("✅ System shutdown complete")


if __name__ == "__main__":
    # Run the system
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 System crash: {e}")
        logging.error(f"System crash: {e}", exc_info=True)