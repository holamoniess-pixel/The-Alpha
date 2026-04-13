"""
Intelligence Engine - AI brain for command processing
Natural language understanding and intent classification
"""

from typing import Dict, Any, Optional
import asyncio
import re
from datetime import datetime

class IntelligenceEngine:
    """
    AI reasoning and command processing
    """
    
    def __init__(self, model_name: str, memory_system):
        self.model_name = model_name
        self.memory = memory_system
        self.automation = None
        
        self.llm = None
        self.intent_classifier = None
    
    async def initialize(self):
        """Load AI models"""
        # Initialize simple LLM fallback
        self.llm = SimpleLLM()
        
        # Initialize intent classifier
        self.intent_classifier = IntentClassifier()
    
    async def process_command(self, command: str) -> str:
        """Process user command and return response"""
        try:
            print(f"Processing command: {command}")
            
            # Classify intent
            intent = await self.intent_classifier.classify(command)
            
            # Get relevant context from memory
            context = await self.memory.retrieve_context(command)
            
            # Route to appropriate handler
            if intent.type == "automation":
                return await self.handle_automation(command, intent, context)
            
            elif intent.type == "information":
                return await self.handle_information(command, context)
            
            elif intent.type == "system_control":
                return await self.handle_system_control(command, intent)
            
            else:
                return await self.handle_general(command, context)
        
        except Exception as e:
            return f"I encountered an error: {str(e)}"
    
    async def handle_automation(self, command: str, intent, context: str) -> str:
        """Handle automation commands"""
        if self.automation:
            result = await self.automation.execute_command(command, intent)
            return result
        else:
            return "Automation system not available"
    
    async def handle_information(self, command: str, context: str) -> str:
        """Handle information queries"""
        # Handle common information requests
        command_lower = command.lower()
        
        if "what time" in command_lower:
            from datetime import datetime
            current_time = datetime.now().strftime("%I:%M %p")
            return f"The current time is {current_time}"
        
        elif "what date" in command_lower:
            from datetime import datetime
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {current_date}"
        
        elif "who are you" in command_lower or "what are you" in command_lower:
            return "I am Alpha, your voice-controlled AI assistant. I can help you control your computer and automate tasks."
        
        elif "what can you do" in command_lower:
            return "I can open applications, type text, click buttons, minimize windows, and learn from your habits to automate repetitive tasks."
        
        # Use LLM for other queries
        return await self.llm.generate_response(command, context)
    
    async def handle_system_control(self, command: str, intent) -> str:
        """Handle system control commands"""
        # Parse control action
        action = intent.entities.get('action')
        target = intent.entities.get('target')
        
        if action == "open":
            result = await self.automation.open_application(target)
            return f"Opening {target}"
        
        elif action == "close":
            result = await self.automation.close_application(target)
            return f"Closing {target}"
        
        elif action == "minimize":
            result = await self.automation.minimize_window(target)
            return f"Minimizing {target}"
        
        elif action == "type":
            text = intent.entities.get('text', '')
            await self.automation.type_text(text)
            return f"Typed: {text}"
        
        elif action == "click":
            x = intent.entities.get('x', 0)
            y = intent.entities.get('y', 0)
            await self.automation.click_position(x, y)
            return f"Clicked at {x}, {y}"
        
        else:
            return "I'm not sure how to do that"
    
    async def handle_general(self, command: str, context: str) -> str:
        """Handle general conversation"""
        return await self.llm.generate_response(command, context)


class SimpleLLM:
    """Simple LLM fallback for basic responses"""
    
    def __init__(self):
        self.responses = {
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! What would you like to do?",
            "thanks": "You're welcome!",
            "thank you": "You're welcome!",
            "goodbye": "Goodbye! I'll be here when you need me.",
            "help": "I can help you open applications, type text, click buttons, and control your computer with voice. Just say 'Hey Alpha' followed by your command."
        }
    
    async def generate_response(self, command: str, context: str) -> str:
        """Generate simple response"""
        command_lower = command.lower().strip()
        
        # Check for simple responses
        for key, response in self.responses.items():
            if key in command_lower:
                return response
        
        # Default response
        return "I understand you said: " + command + ". How can I help with that?"


class IntentClassifier:
    """Classify user intent from commands"""
    
    def __init__(self):
        self.intent_patterns = {
            'automation': [
                'automate', 'create workflow', 'repeat', 'do again',
                'every time', 'when I', 'schedule', 'learn this'
            ],
            'information': [
                'what', 'who', 'when', 'where', 'why', 'how',
                'tell me', 'explain', 'what is', 'what time', 'what date'
            ],
            'system_control': [
                'open', 'close', 'launch', 'start', 'stop',
                'minimize', 'maximize', 'switch to', 'type', 'click'
            ]
        }
    
    async def classify(self, command: str) -> 'Intent':
        """Classify command intent"""
        command_lower = command.lower()
        
        # Check patterns
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in command_lower:
                    return Intent(
                        type=intent_type,
                        confidence=0.8,
                        entities=self.extract_entities(command, intent_type)
                    )
        
        # Default to general
        return Intent(
            type='general',
            confidence=0.5,
            entities={}
        )
    
    def extract_entities(self, command: str, intent_type: str) -> Dict:
        """Extract entities from command"""
        entities = {}
        command_lower = command.lower()
        
        if intent_type == 'system_control':
            # Extract action and target
            words = command_lower.split()
            
            for i, word in enumerate(words):
                if word in ['open', 'close', 'launch', 'start', 'stop', 'minimize']:
                    entities['action'] = word
                    if i + 1 < len(words):
                        entities['target'] = words[i + 1]
                    break
            
            # Extract coordinates for click
            if 'click' in command_lower:
                # Look for numbers in command
                numbers = re.findall(r'\d+', command)
                if len(numbers) >= 2:
                    entities['x'] = int(numbers[0])
                    entities['y'] = int(numbers[1])
            
            # Extract text for type
            if 'type' in command_lower:
                # Extract quoted text or text after 'type'
                match = re.search(r'type\s+(.+)', command_lower)
                if match:
                    entities['text'] = match.group(1)
        
        return entities


class Intent:
    """Intent data structure"""
    def __init__(self, type: str, confidence: float, entities: Dict):
        self.type = type
        self.confidence = confidence
        self.entities = entities
