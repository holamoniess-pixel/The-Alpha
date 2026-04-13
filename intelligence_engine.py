#!/usr/bin/env python3
"""
ALPHA OMEGA - INTELLIGENCE ENGINE
Advanced AI processing with local LLM integration
Version: 1.1.0 Production Ready
"""

import asyncio
import json
import logging
import torch
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import requests
import time
import hashlib
from transformers import AutoTokenizer, AutoModelForCausalLM
import openai

class IntentType(Enum):
    AUTOMATION = "automation"
    QUERY = "query"
    SYSTEM = "system"
    LEARNING = "learning"
    CONVERSATION = "conversation"

@dataclass
class ProcessedIntent:
    type: IntentType
    confidence: float
    command: str
    parameters: Dict[str, Any]
    context: Dict[str, Any]

class IntelligenceEngine:
    """
    Advanced AI processing engine with local LLM support
    """
    
    def __init__(self, config: Dict, memory_system):
        self.config = config
        self.memory_system = memory_system
        self.logger = logging.getLogger('IntelligenceEngine')
        
        # Model components
        self.tokenizer = None
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Intent recognition
        self.intent_patterns = self._load_intent_patterns()
        self.context_window = []
        self.max_context = config.get('context_window', 4096)
        
        # Performance metrics
        self.processing_time = 0
        self.intent_accuracy = 0.0
        
    async def initialize(self):
        """Initialize AI models and components"""
        self.logger.info("Initializing Intelligence Engine...")
        
        try:
            # Load local LLM model
            await self._load_llm_model()
            
            # Initialize intent recognition
            self._initialize_intent_recognition()
            
            # Load knowledge base
            await self._load_knowledge_base()
            
            self.logger.info("Intelligence Engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Intelligence Engine initialization failed: {e}")
            raise
    
    async def _load_llm_model(self):
        """Load local LLM model"""
        model_name = self.config.get('llm_model', 'microsoft/DialoGPT-medium')
        
        try:
            self.logger.info(f"Loading LLM model: {model_name}")
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            # Set pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.logger.info("LLM model loaded successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to load local model: {e}")
            self.logger.info("Falling back to API-based processing")
            
            # Initialize API client as fallback
            await self._initialize_api_fallback()
    
    async def _initialize_api_fallback(self):
        """Initialize API fallback for LLM processing"""
        # This would connect to OpenRouter or similar service
        # For now, using a simple rule-based approach
        self.api_fallback = True
        self.logger.info("API fallback mode enabled")
    
    def _load_intent_patterns(self) -> Dict[str, Any]:
        """Load intent recognition patterns"""
        return {
            'automation': {
                'keywords': ['open', 'start', 'run', 'launch', 'click', 'type', 'press'],
                'examples': [
                    'open calculator',
                    'start notepad',
                    'click on the button',
                    'type hello world'
                ]
            },
            'query': {
                'keywords': ['what', 'how', 'when', 'where', 'why', 'who'],
                'examples': [
                    'what time is it',
                    'how do I do this',
                    'what is the weather'
                ]
            },
            'system': {
                'keywords': ['status', 'help', 'restart', 'shutdown', 'config'],
                'examples': [
                    'system status',
                    'show help',
                    'restart system'
                ]
            },
            'learning': {
                'keywords': ['learn', 'remember', 'forget', 'pattern', 'habit'],
                'examples': [
                    'learn this pattern',
                    'remember my preference',
                    'forget this command'
                ]
            }
        }
    
    def _initialize_intent_recognition(self):
        """Initialize intent recognition system"""
        self.intent_classifier = IntentClassifier(self.intent_patterns)
        self.logger.info("Intent recognition initialized")
    
    async def _load_knowledge_base(self):
        """Load system knowledge base"""
        self.knowledge_base = {
            'system_commands': {
                'status': 'Get system status',
                'help': 'Show available commands',
                'restart': 'Restart the system',
                'shutdown': 'Shutdown the system'
            },
            'automation_commands': {
                'open': 'Open applications',
                'click': 'Click at coordinates',
                'type': 'Type text',
                'screenshot': 'Take screenshot'
            },
            'common_responses': {
                'greeting': 'Hello! Alpha Omega is ready to assist you.',
                'ready': 'System is online and ready.',
                'error': 'I encountered an error processing your request.'
            }
        }
    
    async def process_command(self, command: str) -> ProcessedIntent:
        """Process natural language command"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing command: {command}")
            
            # Add to context window
            self.context_window.append({
                'timestamp': time.time(),
                'command': command,
                'type': 'input'
            })
            
            # Maintain context window size
            if len(self.context_window) > 100:
                self.context_window = self.context_window[-100:]
            
            # Intent recognition
            intent = await self._recognize_intent(command)
            
            # Context enhancement
            intent = await self._enhance_with_context(intent)
            
            # Store in memory
            if self.memory_system:
                await self.memory_system.store_command(
                    command, intent.type.value, True, "", intent.context
                )
            
            self.processing_time = time.time() - start_time
            self.logger.info(f"Intent processed: {intent.type.value} (confidence: {intent.confidence:.2f})")
            
            return intent
            
        except Exception as e:
            self.logger.error(f"Command processing error: {e}")
            self.processing_time = time.time() - start_time
            
            # Return error intent
            return ProcessedIntent(
                type=IntentType.CONVERSATION,
                confidence=0.0,
                command="error",
                parameters={'error': str(e)},
                context={}
            )
    
    async def _recognize_intent(self, command: str) -> ProcessedIntent:
        """Recognize intent from command"""
        # Use intent classifier
        intent_result = self.intent_classifier.classify(command)
        
        # Create processed intent
        return ProcessedIntent(
            type=IntentType(intent_result['type']),
            confidence=intent_result['confidence'],
            command=command,
            parameters=intent_result['parameters'],
            context={'raw_command': command}
        )
    
    async def _enhance_with_context(self, intent: ProcessedIntent) -> ProcessedIntent:
        """Enhance intent with contextual information"""
        # Add recent context
        recent_context = [ctx for ctx in self.context_window[-5:] if ctx['type'] == 'input']
        intent.context['recent_commands'] = recent_context
        
        # Add system state
        intent.context['system_state'] = {
            'time': time.time(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Check for patterns in memory
        if self.memory_system:
            patterns = await self.memory_system.get_patterns('command', limit=5)
            intent.context['relevant_patterns'] = patterns
        
        return intent
    
    async def answer_query(self, intent: ProcessedIntent) -> str:
        """Answer informational queries"""
        query = intent.parameters.get('query', intent.command)
        
        # Check knowledge base first
        for category, knowledge in self.knowledge_base.items():
            for key, value in knowledge.items():
                if key.lower() in query.lower():
                    return str(value)
        
        # Use LLM for complex queries
        if self.model:
            return await self._generate_llm_response(query, intent.context)
        else:
            return await self._generate_rule_based_response(query, intent.context)
    
    async def _generate_llm_response(self, query: str, context: Dict) -> str:
        """Generate response using local LLM"""
        try:
            # Prepare prompt
            prompt = f"""System: You are Alpha Omega, an intelligent AI assistant.
User: {query}
Context: {json.dumps(context, indent=2)}

Please provide a helpful and accurate response:"""
            
            # Tokenize input
            inputs = self.tokenizer.encode(prompt, return_tensors='pt').to(self.device)
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + self.config.get('max_tokens', 512),
                    temperature=self.config.get('temperature', 0.7),
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"LLM generation error: {e}")
            return "I apologize, but I'm having trouble processing that request."
    
    async def _generate_rule_based_response(self, query: str, context: Dict) -> str:
        """Generate response using rule-based approach"""
        # Simple rule-based responses
        if 'time' in query.lower():
            return f"The current time is {time.strftime('%H:%M:%S')}"
        elif 'date' in query.lower():
            return f"Today is {time.strftime('%A, %B %d, %Y')}"
        elif 'weather' in query.lower():
            return "I don't have access to weather data right now."
        else:
            return "I'm not sure how to answer that. Try asking about system status or available commands."
    
    def set_memory_system(self, memory_system):
        """Set memory system reference"""
        self.memory_system = memory_system
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine performance metrics"""
        return {
            'processing_time': self.processing_time,
            'intent_accuracy': self.intent_accuracy,
            'context_window_size': len(self.context_window),
            'model_loaded': self.model is not None,
            'api_fallback': getattr(self, 'api_fallback', False)
        }


class IntentClassifier:
    """Advanced intent classification system"""
    
    def __init__(self, patterns: Dict[str, Any]):
        self.patterns = patterns
        self.logger = logging.getLogger('IntentClassifier')
    
    def classify(self, command: str) -> Dict[str, Any]:
        """Classify command intent with confidence scoring"""
        command_lower = command.lower()
        scores = {}
        
        # Calculate scores for each intent type
        for intent_type, pattern_data in self.patterns.items():
            score = 0.0
            
            # Keyword matching
            keywords = pattern_data.get('keywords', [])
            for keyword in keywords:
                if keyword in command_lower:
                    score += 0.3
            
            # Example matching (simple similarity)
            examples = pattern_data.get('examples', [])
            for example in examples:
                similarity = self._calculate_similarity(command_lower, example.lower())
                score += similarity * 0.2
            
            # Normalize score
            max_possible = len(keywords) * 0.3 + len(examples) * 0.2
            normalized_score = score / max_possible if max_possible > 0 else 0
            
            scores[intent_type] = min(normalized_score, 1.0)
        
        # Find best match
        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent]
        
        # Extract parameters
        parameters = self._extract_parameters(command_lower, best_intent)
        
        return {
            'type': best_intent,
            'confidence': confidence,
            'parameters': parameters
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        # Simple word overlap similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_parameters(self, command: str, intent_type: str) -> Dict[str, Any]:
        """Extract parameters from command"""
        parameters = {}
        
        if intent_type == 'automation':
            # Extract automation parameters
            words = command.split()
            for i, word in enumerate(words):
                if word in ['open', 'start', 'run', 'launch']:
                    if i + 1 < len(words):
                        parameters['action'] = word
                        parameters['target'] = ' '.join(words[i+1:])
                        break
        
        elif intent_type == 'query':
            # Extract query parameters
            parameters['query'] = command
        
        return parameters


# Example usage and testing
if __name__ == "__main__":
    # Test the intelligence engine
    async def test_engine():
        # Mock memory system
        class MockMemory:
            async def store_command(self, *args, **kwargs):
                pass
            async def get_patterns(self, *args, **kwargs):
                return []
        
        config = {
            'llm_model': 'microsoft/DialoGPT-medium',
            'context_window': 2048,
            'temperature': 0.7,
            'max_tokens': 256
        }
        
        engine = IntelligenceEngine(config, MockMemory())
        await engine.initialize()
        
        # Test commands
        test_commands = [
            "open calculator",
            "what time is it",
            "system status",
            "learn this pattern"
        ]
        
        for command in test_commands:
            print(f"\nTesting: {command}")
            intent = await engine.process_command(command)
            print(f"Intent: {intent.type.value} (confidence: {intent.confidence:.2f})")
            print(f"Parameters: {intent.parameters}")
        
        print("\nEngine metrics:", engine.get_metrics())
    
    asyncio.run(test_engine())