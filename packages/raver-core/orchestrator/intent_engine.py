"""
Intent Engine - Parses user requests and determines intended actions.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ...raver_shared.schemas import ActionType


@dataclass
class Intent:
    """Parsed user intent."""
    action_type: ActionType
    target_resource: str
    parameters: Dict[str, Any]
    confidence: float
    raw_text: str


class IntentEngine:
    """Engine for parsing user intent from natural language."""
    
    def __init__(self):
        self.action_patterns = {
            ActionType.PROCESS_TERMINATE: [
                r"(?:kill|terminate|stop|end|close)\s+(?:process\s+)?(.+)",
                r"(?:shutdown|kill)\s+(.+)",
                r"stop\s+(?:the\s+)?process\s+(.+)"
            ],
            ActionType.FILE_MODIFY: [
                r"(?:create|write|edit|modify|update|delete)\s+(?:file\s+)?(.+)",
                r"(?:make|generate)\s+(?:a\s+)?file\s+(.+)",
                r"(?:remove|delete)\s+(?:file\s+)?(.+)"
            ],
            ActionType.VAULT_ACCESS: [
                r"(?:get|retrieve|fetch|access)\s+(?:secret|password|credential)\s+(?:for\s+)?(.+)",
                r"(?:store|save)\s+(?:secret|password|credential)\s+(?:for\s+)?(.+)",
                r"(?:vault|secret)\s+(?:get|store|save)\s+(.+)"
            ],
            ActionType.UI_AUTOMATION: [
                r"(?:click|press)\s+(?:at\s+)?(?:coordinate\s+)?(.+)",
                r"(?:type|enter)\s+(?:text\s+)?(.+)",
                r"(?:automate|control)\s+(.+)",
                r"(?:move\s+)?mouse\s+(?:to\s+)?(.+)"
            ],
            ActionType.LINK_INSPECT: [
                r"(?:check|inspect|scan|verify)\s+(?:link|url)\s+(.+)",
                r"(?:is\s+)?(.+)\s+(?:safe|suspicious|malicious)",
                r"(?:open\s+)?(?:in\s+)?(?:sandbox|isolated)\s+(.+)"
            ],
            ActionType.SYSTEM_SCAN: [
                r"(?:scan|check)\s+(?:system|computer)",
                r"(?:run\s+)?(?:security|virus)\s+scan",
                r"(?:check\s+)?(?:for\s+)?(?:threats|malware)"
            ]
        }
        
        self.parameter_extractors = {
            "coordinates": r"(\d+)\s*[,\s]\s*(\d+)",
            "file_content": r"(?:with|containing)\s+['\"](.+?)['\"]",
            "process_name": r"(.+\.exe)",
            "url_pattern": r"https?://[^\s]+",
            "secret_service": r"(?:for|service)\s+(\w+)",
            "secret_label": r"(?:label|name)\s+(\w+)"
        }
    
    async def initialize(self):
        """Initialize the intent engine."""
        # Initialize any ML models or additional resources
        pass
    
    async def get_status(self) -> Dict[str, Any]:
        """Get intent engine status."""
        return {
            "initialized": True,
            "supported_actions": [action.value for action in ActionType],
            "patterns_count": sum(len(patterns) for patterns in self.action_patterns.values())
        }
    
    async def parse_intent(self, text: str, context: Dict[str, Any] = None) -> Intent:
        """
        Parse user text to determine intent.
        
        Args:
            text: User input text
            context: Additional context for intent parsing
            
        Returns:
            Intent object with parsed action and parameters
        """
        text = text.strip().lower()
        
        # Try to match action patterns
        best_match = None
        best_confidence = 0.0
        
        for action_type, patterns in self.action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    confidence = self._calculate_confidence(text, pattern, match)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (action_type, match)
        
        if best_match:
            action_type, match = best_match
            target_resource = match.group(1).strip() if match.groups() else ""
            parameters = self._extract_parameters(text, action_type, context)
            
            return Intent(
                action_type=action_type,
                target_resource=target_resource,
                parameters=parameters,
                confidence=best_confidence,
                raw_text=text
            )
        
        # Default to unknown intent
        return Intent(
            action_type=ActionType.UI_AUTOMATION,  # Default action
            target_resource="",
            parameters={},
            confidence=0.0,
            raw_text=text
        )
    
    def _calculate_confidence(self, text: str, pattern: str, match: re.Match) -> float:
        """Calculate confidence score for pattern match."""
        base_confidence = 0.8
        
        # Boost confidence for exact matches
        if match.group(0) == text:
            base_confidence += 0.1
        
        # Boost for specific keywords
        specific_keywords = ["kill", "terminate", "create", "delete", "click", "scan"]
        for keyword in specific_keywords:
            if keyword in text:
                base_confidence += 0.05
        
        # Boost for complete target resource
        if match.groups() and match.group(1):
            target = match.group(1).strip()
            if len(target) > 3:  # Reasonable length target
                base_confidence += 0.05
        
        return min(base_confidence, 1.0)
    
    def _extract_parameters(self, text: str, action_type: ActionType, 
                           context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract parameters from text based on action type."""
        parameters = {}
        
        # Extract common parameters
        for param_name, pattern in self.parameter_extractors.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if param_name == "coordinates":
                    parameters["x"] = int(match.group(1))
                    parameters["y"] = int(match.group(2))
                elif param_name == "file_content":
                    parameters["content"] = match.group(1)
                elif param_name == "process_name":
                    parameters["process_name"] = match.group(1)
                elif param_name == "url_pattern":
                    parameters["url"] = match.group(0)
                elif param_name == "secret_service":
                    parameters["service"] = match.group(1)
                elif param_name == "secret_label":
                    parameters["label"] = match.group(1)
        
        # Action-specific parameter extraction
        if action_type == ActionType.FILE_MODIFY:
            if "create" in text or "write" in text:
                parameters["operation"] = "write"
            elif "delete" in text or "remove" in text:
                parameters["operation"] = "delete"
            elif "append" in text or "add" in text:
                parameters["operation"] = "append"
            else:
                parameters["operation"] = "write"
        
        elif action_type == ActionType.UI_AUTOMATION:
            if "click" in text or "press" in text:
                parameters["action"] = "click"
            elif "type" in text or "enter" in text:
                parameters["action"] = "type"
                # Extract text to type
                type_match = re.search(r"type\s+['\"](.+?)['\"]", text, re.IGNORECASE)
                if type_match:
                    parameters["text"] = type_match.group(1)
            elif "move" in text:
                parameters["action"] = "move"
            else:
                parameters["action"] = "click"
        
        elif action_type == ActionType.VAULT_ACCESS:
            if "get" in text or "retrieve" in text or "fetch" in text:
                parameters["operation"] = "read"
            elif "store" in text or "save" in text:
                parameters["operation"] = "create"
            else:
                parameters["operation"] = "read"
        
        elif action_type == ActionType.LINK_INSPECT:
            if "sandbox" in text or "isolated" in text:
                parameters["mode"] = "sandbox"
            else:
                parameters["mode"] = "standard"
        
        # Add context parameters
        if context:
            parameters.update(context)
        
        return parameters
    
    async def get_intent_suggestions(self, partial_text: str) -> List[str]:
        """Get suggestions for completing partial user input."""
        suggestions = []
        partial_lower = partial_text.lower()
        
        # Action-based suggestions
        for action_type, patterns in self.action_patterns.items():
            for pattern in patterns:
                # Remove capture groups for suggestion
                suggestion = re.sub(r'\(.+?\)', '', pattern).strip()
                if partial_lower in suggestion[:len(partial_lower)]:
                    suggestions.append(suggestion)
        
        # Remove duplicates and limit
        suggestions = list(set(suggestions))[:5]
        return suggestions
    
    def get_supported_actions(self) -> List[str]:
        """Get list of supported action types."""
        return [action.value for action in ActionType]
