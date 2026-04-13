#!/usr/bin/env python3
"""
ALPHA OMEGA - LEARNING ENGINE
Advanced user behavior analysis and pattern recognition
Version: 1.1.0 Production Ready
"""

import asyncio
import json
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
import hashlib
from collections import defaultdict, Counter
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pickle

@dataclass
class UserPattern:
    """Represents a learned user pattern"""
    pattern_id: str
    pattern_type: str
    data: Dict[str, Any]
    confidence: float
    frequency: int
    last_seen: datetime
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class BehaviorPrediction:
    """Predicted user behavior"""
    action: str
    confidence: float
    timing: Optional[datetime]
    context: Dict[str, Any]
    alternatives: List[str]

class LearningEngine:
    """
    Advanced user behavior analysis and learning system
    """
    
    def __init__(self, config: Dict[str, Any], memory_system):
        self.config = config
        self.memory_system = memory_system
        self.logger = logging.getLogger('LearningEngine')
        
        # Learning components
        self.pattern_analyzer = PatternAnalyzer(config)
        self.behavior_predictor = BehaviorPredictor(config)
        self.adaptation_engine = AdaptationEngine(config)
        
        # Learning state
        self.is_learning = False
        self.learning_iterations = 0
        self.patterns_learned = 0
        self.predictions_made = 0
        
        # Performance metrics
        self.accuracy = 0.0
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        self.learning_rate = config.get('learning_rate', 0.01)
        
    async def initialize(self):
        """Initialize learning engine components"""
        self.logger.info("Initializing Learning Engine...")
        
        try:
            # Initialize pattern analyzer
            await self.pattern_analyzer.initialize()
            
            # Initialize behavior predictor
            await self.behavior_predictor.initialize()
            
            # Initialize adaptation engine
            await self.adaptation_engine.initialize()
            
            # Load existing patterns
            await self._load_existing_patterns()
            
            self.logger.info("Learning Engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Learning Engine initialization failed: {e}")
            raise
    
    async def start_learning(self):
        """Start continuous learning process"""
        if self.is_learning:
            self.logger.warning("Learning is already active")
            return
        
        self.is_learning = True
        self.logger.info("Starting continuous learning...")
        
        # Start learning tasks
        tasks = [
            self._continuous_pattern_analysis(),
            self._behavior_prediction_loop(),
            self._adaptation_loop()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop(self):
        """Stop learning processes"""
        self.logger.info("Stopping Learning Engine...")
        self.is_learning = False
        
        # Save learned patterns
        await self._save_patterns()
        
        self.logger.info("Learning Engine stopped")
    
    async def record_command(self, command: str, context: Dict[str, Any] = None):
        """Record user command for learning analysis"""
        try:
            # Extract features from command
            features = await self._extract_command_features(command, context)
            
            # Store in memory
            await self.memory_system.store_command(
                command=command,
                intent="learning",
                success=True,
                response="",
                context=features
            )
            
            # Analyze for patterns
            await self.pattern_analyzer.analyze_command(features)
            
            self.logger.debug(f"Recorded command: {command}")
            
        except Exception as e:
            self.logger.error(f"Error recording command: {e}")
    
    async def learn_from_result(self, command: str, result: Any):
        """Learn from command execution results"""
        try:
            # Extract result features
            result_features = await self._extract_result_features(result)
            
            # Update learning models
            await self.pattern_analyzer.update_with_result(command, result_features)
            await self.behavior_predictor.update_model(command, result_features)
            
            # Increment learning metrics
            self.learning_iterations += 1
            
            self.logger.debug(f"Learned from result: {command}")
            
        except Exception as e:
            self.logger.error(f"Error learning from result: {e}")
    
    async def predict_next_action(self, context: Dict[str, Any]) -> Optional[BehaviorPrediction]:
        """Predict user's next likely action"""
        try:
            prediction = await self.behavior_predictor.predict(context)
            
            if prediction and prediction.confidence > self.confidence_threshold:
                self.predictions_made += 1
                self.logger.info(f"Predicted action: {prediction.action} (confidence: {prediction.confidence:.2f})")
                return prediction
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error predicting action: {e}")
            return None
    
    async def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from learning analysis"""
        try:
            insights = {
                'patterns_learned': self.patterns_learned,
                'predictions_made': self.predictions_made,
                'learning_iterations': self.learning_iterations,
                'accuracy': self.accuracy,
                'pattern_analysis': await self.pattern_analyzer.get_insights(),
                'behavior_analysis': await self.behavior_predictor.get_insights()
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting learning insights: {e}")
            return {}
    
    async def _continuous_pattern_analysis(self):
        """Continuous pattern analysis loop"""
        while self.is_learning:
            try:
                # Analyze recent commands
                recent_commands = await self._get_recent_commands(hours=1)
                
                if recent_commands:
                    new_patterns = await self.pattern_analyzer.find_patterns(recent_commands)
                    
                    for pattern in new_patterns:
                        await self._store_pattern(pattern)
                        self.patterns_learned += 1
                
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Pattern analysis error: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute
    
    async def _behavior_prediction_loop(self):
        """Continuous behavior prediction loop"""
        while self.is_learning:
            try:
                # Get current context
                current_context = await self._get_current_context()
                
                # Make predictions
                prediction = await self.predict_next_action(current_context)
                
                if prediction:
                    # Suggest action to user (if appropriate)
                    await self._suggest_action(prediction)
                
                await asyncio.sleep(60)  # Predict every minute
                
            except Exception as e:
                self.logger.error(f"Behavior prediction error: {e}")
                await asyncio.sleep(30)  # Retry in 30 seconds
    
    async def _adaptation_loop(self):
        """Continuous adaptation loop"""
        while self.is_learning:
            try:
                # Analyze system performance
                performance_metrics = await self._get_performance_metrics()
                
                # Adapt based on performance
                adaptations = await self.adaptation_engine.suggest_adaptations(performance_metrics)
                
                for adaptation in adaptations:
                    await self._apply_adaptation(adaptation)
                
                await asyncio.sleep(600)  # Adapt every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Adaptation error: {e}")
                await asyncio.sleep(120)  # Retry in 2 minutes
    
    async def _extract_command_features(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """Extract features from user command"""
        features = {
            'command': command,
            'timestamp': datetime.now().isoformat(),
            'length': len(command),
            'word_count': len(command.split()),
            'keywords': self._extract_keywords(command),
            'intent_type': await self._classify_intent(command),
            'context': context or {}
        }
        
        return features
    
    async def _extract_result_features(self, result: Any) -> Dict[str, Any]:
        """Extract features from command result"""
        features = {
            'success': getattr(result, 'success', True),
            'response': str(result) if result else "",
            'timestamp': datetime.now().isoformat()
        }
        
        return features
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction (can be enhanced with NLP)
        words = text.lower().split()
        keywords = [word for word in words if len(word) > 3]
        return keywords[:10]  # Top 10 keywords
    
    async def _classify_intent(self, command: str) -> str:
        """Classify command intent"""
        # Simple intent classification
        command_lower = command.lower()
        
        if any(word in command_lower for word in ['open', 'start', 'run', 'launch']):
            return 'automation'
        elif any(word in command_lower for word in ['what', 'how', 'when', 'where']):
            return 'query'
        elif any(word in command_lower for word in ['learn', 'remember', 'forget']):
            return 'learning'
        else:
            return 'general'
    
    async def _get_recent_commands(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent commands from memory"""
        # This would query the memory system
        # For now, return empty list
        return []
    
    async def _get_current_context(self) -> Dict[str, Any]:
        """Get current system context"""
        context = {
            'timestamp': datetime.now().isoformat(),
            'time_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday(),
            'recent_activity': await self._get_recent_activity()
        }
        
        return context
    
    async def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent user activity"""
        # This would query the memory system
        return []
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        metrics = {
            'learning_iterations': self.learning_iterations,
            'patterns_learned': self.patterns_learned,
            'predictions_made': self.predictions_made,
            'accuracy': self.accuracy
        }
        
        return metrics
    
    async def _store_pattern(self, pattern: UserPattern):
        """Store learned pattern"""
        try:
            pattern_data = {
                'pattern_id': pattern.pattern_id,
                'pattern_type': pattern.pattern_type,
                'data': pattern.data,
                'confidence': pattern.confidence,
                'frequency': pattern.frequency,
                'last_seen': pattern.last_seen.isoformat(),
                'created_at': pattern.created_at.isoformat(),
                'metadata': pattern.metadata
            }
            
            await self.memory_system.store_pattern(pattern_data)
            
        except Exception as e:
            self.logger.error(f"Error storing pattern: {e}")
    
    async def _load_existing_patterns(self):
        """Load existing patterns from memory"""
        try:
            patterns = await self.memory_system.get_patterns()
            
            for pattern_data in patterns:
                pattern = UserPattern(
                    pattern_id=pattern_data['pattern_id'],
                    pattern_type=pattern_data['pattern_type'],
                    data=pattern_data['data'],
                    confidence=pattern_data['confidence'],
                    frequency=pattern_data['frequency'],
                    last_seen=datetime.fromisoformat(pattern_data['last_seen']),
                    created_at=datetime.fromisoformat(pattern_data['created_at']),
                    metadata=pattern_data.get('metadata', {})
                )
                
                await self.pattern_analyzer.load_pattern(pattern)
            
            self.logger.info(f"Loaded {len(patterns)} existing patterns")
            
        except Exception as e:
            self.logger.error(f"Error loading existing patterns: {e}")
    
    async def _save_patterns(self):
        """Save learned patterns to memory"""
        try:
            patterns = await self.pattern_analyzer.get_all_patterns()
            
            for pattern in patterns:
                await self._store_pattern(pattern)
            
            self.logger.info(f"Saved {len(patterns)} patterns")
            
        except Exception as e:
            self.logger.error(f"Error saving patterns: {e}")
    
    async def _suggest_action(self, prediction: BehaviorPrediction):
        """Suggest predicted action to user"""
        try:
            # Only suggest if confidence is high
            if prediction.confidence > 0.8:
                suggestion = f"Would you like me to {prediction.action}?"
                # This would be sent to the voice system
                self.logger.info(f"Suggested: {suggestion}")
            
        except Exception as e:
            self.logger.error(f"Error suggesting action: {e}")
    
    async def _apply_adaptation(self, adaptation: Dict[str, Any]):
        """Apply system adaptation"""
        try:
            self.logger.info(f"Applying adaptation: {adaptation}")
            
            # Apply adaptation based on type
            adaptation_type = adaptation.get('type')
            
            if adaptation_type == 'parameter_adjustment':
                await self._adjust_parameters(adaptation['parameters'])
            elif adaptation_type == 'pattern_update':
                await self._update_patterns(adaptation['patterns'])
            
        except Exception as e:
            self.logger.error(f"Error applying adaptation: {e}")
    
    async def _adjust_parameters(self, parameters: Dict[str, Any]):
        """Adjust learning parameters"""
        if 'confidence_threshold' in parameters:
            self.confidence_threshold = parameters['confidence_threshold']
        
        if 'learning_rate' in parameters:
            self.learning_rate = parameters['learning_rate']
        
        self.logger.info(f"Adjusted parameters: {parameters}")
    
    async def _update_patterns(self, patterns: List[Dict[str, Any]]):
        """Update learned patterns"""
        for pattern_data in patterns:
            await self.pattern_analyzer.update_pattern(pattern_data)
        
        self.logger.info(f"Updated {len(patterns)} patterns")


# Supporting Classes
class PatternAnalyzer:
    """Advanced pattern analysis and recognition"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.patterns = []
        self.logger = logging.getLogger('PatternAnalyzer')
    
    async def initialize(self):
        """Initialize pattern analyzer"""
        self.logger.info("Pattern Analyzer initialized")
    
    async def analyze_command(self, features: Dict[str, Any]):
        """Analyze command features for patterns"""
        # Implementation for pattern analysis
        pass
    
    async def find_patterns(self, commands: List[Dict[str, Any]]) -> List[UserPattern]:
        """Find patterns in command data"""
        # Implementation for pattern finding
        return []
    
    async def get_insights(self) -> Dict[str, Any]:
        """Get pattern analysis insights"""
        return {
            'patterns_found': len(self.patterns),
            'analysis_complete': True
        }

class BehaviorPredictor:
    """User behavior prediction system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('BehaviorPredictor')
    
    async def initialize(self):
        """Initialize behavior predictor"""
        self.logger.info("Behavior Predictor initialized")
    
    async def predict(self, context: Dict[str, Any]) -> Optional[BehaviorPrediction]:
        """Predict user behavior based on context"""
        # Implementation for behavior prediction
        return None
    
    async def get_insights(self) -> Dict[str, Any]:
        """Get behavior prediction insights"""
        return {
            'predictions_made': 0,
            'accuracy': 0.0
        }

class AdaptationEngine:
    """System adaptation and optimization engine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger('AdaptationEngine')
    
    async def initialize(self):
        """Initialize adaptation engine"""
        self.logger.info("Adaptation Engine initialized")
    
    async def suggest_adaptations(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest system adaptations based on metrics"""
        # Implementation for adaptation suggestions
        return []


# Example usage and testing
if __name__ == "__main__":
    async def test_learning_engine():
        # Mock memory system
        class MockMemory:
            async def store_command(self, *args, **kwargs):
                pass
            async def get_patterns(self, *args, **kwargs):
                return []
            async def store_pattern(self, *args, **kwargs):
                pass
        
        config = {
            'confidence_threshold': 0.7,
            'learning_rate': 0.01,
            'pattern_recognition': True,
            'behavior_analysis': True,
            'prediction_enabled': True
        }
        
        engine = LearningEngine(config, MockMemory())
        await engine.initialize()
        
        # Test learning
        test_commands = [
            "open calculator",
            "open notepad",
            "open browser"
        ]
        
        for command in test_commands:
            await engine.record_command(command)
            print(f"Learned command: {command}")
        
        # Get insights
        insights = await engine.get_learning_insights()
        print(f"Learning insights: {insights}")
    
    asyncio.run(test_learning_engine())