"""
Alpha and Omega - Voice-Activated PC Control System
Main system entry point - orchestrates all components
"""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Dict, Any

class AlphaOmegaSystem:
    """
    Main system class - orchestrates all components
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        self.version = "1.1.0"
        self.config_path = config_path
        self.config = self.load_config()
        
        # Initialize logging
        self.setup_logging()
        
        # Core components
        self.voice_system = None
        self.intelligence_engine = None
        self.learning_system = None
        self.memory_system = None
        self.automation_engine = None
        
        # System state
        self.running = False
        self.initialized = False
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load system configuration"""
        default_config = {
            'wake_word': 'hey alpha',
            'language': 'en',
            'voice_model': 'whisper-base',
            'llm_model': 'llama-7b-q4',
            'memory_limit_mb': 1000,
            'learning_enabled': True,
            'auto_start': True
        }
        
        if Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
        
        return default_config
    
    def setup_logging(self):
        """Configure logging system"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('alpha_omega.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AlphaOmega')
    
    async def initialize(self):
        """Initialize all system components"""
        self.logger.info("Starting Alpha and Omega initialization...")
        
        try:
            # 1. Initialize voice system
            self.logger.info("Initializing voice system...")
            from voice_control import VoiceControlSystem
            self.voice_system = VoiceControlSystem(
                wake_word=self.config['wake_word'],
                language=self.config['language']
            )
            await self.voice_system.initialize()
            
            # 2. Initialize memory system
            self.logger.info("Initializing memory system...")
            from memory_system import MemorySystem
            self.memory_system = MemorySystem(
                cache_size_mb=self.config['memory_limit_mb']
            )
            await self.memory_system.initialize()
            
            # 3. Initialize intelligence engine
            self.logger.info("Loading AI models...")
            from intelligence import IntelligenceEngine
            self.intelligence_engine = IntelligenceEngine(
                model_name=self.config['llm_model'],
                memory_system=self.memory_system
            )
            await self.intelligence_engine.initialize()
            
            # 4. Initialize learning system
            if self.config['learning_enabled']:
                self.logger.info("Initializing learning system...")
                from learning_system import LearningSystem
                self.learning_system = LearningSystem(
                    memory_system=self.memory_system
                )
                await self.learning_system.initialize()
            
            # 5. Initialize automation engine
            self.logger.info("Initializing automation engine...")
            from automation import AutomationEngine
            self.automation_engine = AutomationEngine(
                intelligence=self.intelligence_engine,
                memory=self.memory_system
            )
            await self.automation_engine.initialize()
            
            # 6. Connect components
            self.connect_components()
            
            self.initialized = True
            self.logger.info("System initialized successfully")
            
            # Play ready sound
            await self.play_ready_sound()
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise
    
    def connect_components(self):
        """Wire up component communication"""
        # Voice → Intelligence
        self.voice_system.on_command = self.intelligence_engine.process_command
        
        # Intelligence → Memory
        self.intelligence_engine.memory = self.memory_system
        
        # Intelligence → Automation
        self.intelligence_engine.automation = self.automation_engine
        
        # Learning → Memory
        if self.learning_system:
            self.learning_system.memory = self.memory_system
    
    async def start(self):
        """Start system"""
        if not self.initialized:
            await self.initialize()
        
        self.running = True
        self.logger.info("Alpha and Omega is now running")
        
        # Start all components
        tasks = [
            self.voice_system.start_listening(),
            self.memory_system.start_maintenance(),
        ]
        
        if self.learning_system:
            tasks.append(self.learning_system.start_observing())
        
        # Run all tasks concurrently
        await asyncio.gather(*tasks)
    
    async def stop(self):
        """Gracefully shut down system"""
        self.logger.info("Shutting down system...")
        self.running = False
        
        # Stop all components
        if self.voice_system:
            await self.voice_system.stop()
        
        if self.learning_system:
            await self.learning_system.stop()
        
        if self.memory_system:
            await self.memory_system.save_and_close()
        
        self.logger.info("System shut down complete")
    
    async def play_ready_sound(self):
        """Play sound to indicate system ready"""
        try:
            import winsound
            winsound.Beep(1000, 200)  # 1000 Hz for 200ms
        except:
            pass  # Sound is optional


# Entry point
async def main():
    system = AlphaOmegaSystem()
    
    try:
        await system.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await system.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
