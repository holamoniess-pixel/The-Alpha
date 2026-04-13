#!/usr/bin/env python3
"""
ALPHA OMEGA - VISUAL WORKFLOW BUILDER
Drag-and-drop workflow creation (backend logic)
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class NodeType(Enum):
    ACTION = "action"
    CONDITION = "condition"
    TRIGGER = "trigger"
    LOOP = "loop"
    VARIABLE = "variable"
    DELAY = "delay"
    PARALLEL = "parallel"
    MERGE = "merge"
    SCRIPT = "script"
    HTTP = "http"
    WEBHOOK = "webhook"
    DATABASE = "database"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class PortType(Enum):
    INPUT = "input"
    OUTPUT = "output"
    BOTH = "both"


@dataclass
class NodePort:
    id: str
    name: str
    port_type: PortType
    data_type: str = "any"
    required: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.port_type.value,
            "data_type": self.data_type,
            "required": self.required,
        }


@dataclass
class WorkflowNode:
    id: str
    type: NodeType
    name: str
    position: Tuple[float, float] = (0.0, 0.0)
    size: Tuple[float, float] = (200.0, 100.0)
    inputs: List[NodePort] = field(default_factory=list)
    outputs: List[NodePort] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    category: str = "general"
    icon: str = ""
    color: str = "#4A90D9"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "position": list(self.position),
            "size": list(self.size),
            "inputs": [p.to_dict() for p in self.inputs],
            "outputs": [p.to_dict() for p in self.outputs],
            "properties": self.properties,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowNode":
        inputs = [
            NodePort(
                id=p.get("id", ""),
                name=p.get("name", ""),
                port_type=PortType(p.get("type", "input")),
                data_type=p.get("data_type", "any"),
            )
            for p in data.get("inputs", [])
        ]

        outputs = [
            NodePort(
                id=p.get("id", ""),
                name=p.get("name", ""),
                port_type=PortType(p.get("type", "output")),
                data_type=p.get("data_type", "any"),
            )
            for p in data.get("outputs", [])
        ]

        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            name=data["name"],
            position=tuple(data.get("position", [0, 0])),
            size=tuple(data.get("size", [200, 100])),
            inputs=inputs,
            outputs=outputs,
            properties=data.get("properties", {}),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            icon=data.get("icon", ""),
            color=data.get("color", "#4A90D9"),
        )


@dataclass
class NodeConnection:
    id: str
    source_node_id: str
    source_port_id: str
    target_node_id: str
    target_port_id: str
    label: str = ""
    style: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source_node_id,
            "source_port": self.source_port_id,
            "target": self.target_node_id,
            "target_port": self.target_port_id,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeConnection":
        return cls(
            id=data["id"],
            source_node_id=data["source"],
            source_port_id=data["source_port"],
            target_node_id=data["target"],
            target_port_id=data["target_port"],
            label=data.get("label", ""),
        )


@dataclass
class VisualWorkflow:
    id: str
    name: str
    description: str = ""
    nodes: List[WorkflowNode] = field(default_factory=list)
    connections: List[NodeConnection] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes],
            "connections": [c.to_dict() for c in self.connections],
            "variables": self.variables,
            "settings": self.settings,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualWorkflow":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            nodes=[WorkflowNode.from_dict(n) for n in data.get("nodes", [])],
            connections=[
                NodeConnection.from_dict(c) for c in data.get("connections", [])
            ],
            variables=data.get("variables", {}),
            settings=data.get("settings", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            version=data.get("version", "1.0"),
        )


class NodeTemplate:
    """Pre-defined node templates"""

    TEMPLATES = {
        "trigger_manual": {
            "type": "trigger",
            "name": "Manual Trigger",
            "category": "triggers",
            "description": "Start workflow manually",
            "icon": "play",
            "color": "#28A745",
            "outputs": [{"name": "start", "type": "output"}],
        },
        "trigger_schedule": {
            "type": "trigger",
            "name": "Schedule Trigger",
            "category": "triggers",
            "description": "Start workflow on schedule",
            "icon": "clock",
            "color": "#28A745",
            "properties": {"cron": "0 * * * *"},
            "outputs": [{"name": "start", "type": "output"}],
        },
        "action_open_app": {
            "type": "action",
            "name": "Open Application",
            "category": "actions",
            "description": "Open an application",
            "icon": "app",
            "color": "#4A90D9",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [{"name": "out", "type": "output"}],
            "properties": {"app": "", "args": ""},
        },
        "action_type": {
            "type": "action",
            "name": "Type Text",
            "category": "actions",
            "description": "Type text using keyboard",
            "icon": "keyboard",
            "color": "#4A90D9",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [{"name": "out", "type": "output"}],
            "properties": {"text": ""},
        },
        "action_click": {
            "type": "action",
            "name": "Click Position",
            "category": "actions",
            "description": "Click at screen position",
            "icon": "mouse",
            "color": "#4A90D9",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [{"name": "out", "type": "output"}],
            "properties": {"x": 0, "y": 0},
        },
        "action_screenshot": {
            "type": "action",
            "name": "Take Screenshot",
            "category": "actions",
            "description": "Capture screen",
            "icon": "camera",
            "color": "#4A90D9",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [{"name": "out", "type": "output"}],
        },
        "condition_if": {
            "type": "condition",
            "name": "If Condition",
            "category": "logic",
            "description": "Branch based on condition",
            "icon": "branch",
            "color": "#F5A623",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [
                {"name": "true", "type": "output"},
                {"name": "false", "type": "output"},
            ],
            "properties": {"condition": ""},
        },
        "loop_for": {
            "type": "loop",
            "name": "For Loop",
            "category": "logic",
            "description": "Loop N times",
            "icon": "loop",
            "color": "#F5A623",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [
                {"name": "loop", "type": "output"},
                {"name": "done", "type": "output"},
            ],
            "properties": {"count": 1},
        },
        "delay": {
            "type": "delay",
            "name": "Delay",
            "category": "logic",
            "description": "Wait for specified time",
            "icon": "timer",
            "color": "#F5A623",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [{"name": "out", "type": "output"}],
            "properties": {"seconds": 1},
        },
        "variable_set": {
            "type": "variable",
            "name": "Set Variable",
            "category": "data",
            "description": "Set a variable value",
            "icon": "variable",
            "color": "#9B59B6",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [{"name": "out", "type": "output"}],
            "properties": {"name": "", "value": ""},
        },
        "http_request": {
            "type": "http",
            "name": "HTTP Request",
            "category": "integration",
            "description": "Make HTTP request",
            "icon": "globe",
            "color": "#E74C3C",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [{"name": "response", "type": "output"}],
            "properties": {"method": "GET", "url": "", "headers": {}},
        },
        "notification": {
            "type": "notification",
            "name": "Send Notification",
            "category": "output",
            "description": "Send notification",
            "icon": "bell",
            "color": "#E74C3C",
            "inputs": [{"name": "in", "type": "input"}],
            "outputs": [{"name": "out", "type": "output"}],
            "properties": {"title": "", "message": ""},
        },
    }

    @classmethod
    def create_node(
        cls, template_id: str, position: Tuple[float, float] = (0, 0)
    ) -> Optional[WorkflowNode]:
        """Create a node from template"""
        template = cls.TEMPLATES.get(template_id)
        if not template:
            return None

        node_id = str(uuid.uuid4())[:8]

        inputs = []
        for p in template.get("inputs", []):
            inputs.append(
                NodePort(
                    id=f"{node_id}_in_{p['name']}",
                    name=p["name"],
                    port_type=PortType.INPUT,
                )
            )

        outputs = []
        for p in template.get("outputs", []):
            outputs.append(
                NodePort(
                    id=f"{node_id}_out_{p['name']}",
                    name=p["name"],
                    port_type=PortType.OUTPUT,
                )
            )

        return WorkflowNode(
            id=node_id,
            type=NodeType(template["type"]),
            name=template["name"],
            position=position,
            description=template.get("description", ""),
            category=template.get("category", "general"),
            icon=template.get("icon", ""),
            color=template.get("color", "#4A90D9"),
            inputs=inputs,
            outputs=outputs,
            properties=template.get("properties", {}),
        )

    @classmethod
    def list_templates(cls) -> List[Dict[str, Any]]:
        """List all templates"""
        return [
            {
                "id": tid,
                "name": t["name"],
                "type": t["type"],
                "category": t["category"],
                "description": t.get("description", ""),
                "icon": t.get("icon", ""),
            }
            for tid, t in cls.TEMPLATES.items()
        ]


class VisualWorkflowBuilder:
    """Visual workflow builder backend"""

    def __init__(self, save_dir: str = "data/visual_workflows"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("VisualWorkflowBuilder")

        self._workflows: Dict[str, VisualWorkflow] = {}
        self._load_workflows()

    def _load_workflows(self):
        """Load existing workflows"""
        for workflow_file in self.save_dir.glob("*.json"):
            try:
                with open(workflow_file) as f:
                    data = json.load(f)
                workflow = VisualWorkflow.from_dict(data)
                self._workflows[workflow.id] = workflow
            except Exception as e:
                self.logger.error(f"Error loading workflow: {e}")

    def create_workflow(
        self,
        name: str,
        description: str = "",
    ) -> VisualWorkflow:
        """Create a new visual workflow"""
        workflow_id = str(uuid.uuid4())[:8]

        workflow = VisualWorkflow(
            id=workflow_id,
            name=name,
            description=description,
        )

        self._workflows[workflow_id] = workflow
        self._save_workflow(workflow)

        self.logger.info(f"Created workflow: {name}")
        return workflow

    def _save_workflow(self, workflow: VisualWorkflow):
        """Save workflow to file"""
        workflow_file = self.save_dir / f"{workflow.id}.json"

        with open(workflow_file, "w") as f:
            json.dump(workflow.to_dict(), f, indent=2)

    def add_node(
        self,
        workflow_id: str,
        template_id: str,
        position: Tuple[float, float] = (0, 0),
    ) -> Optional[WorkflowNode]:
        """Add a node to workflow"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        node = NodeTemplate.create_node(template_id, position)
        if not node:
            return None

        workflow.nodes.append(node)
        workflow.updated_at = time.time()
        self._save_workflow(workflow)

        return node

    def add_custom_node(
        self,
        workflow_id: str,
        node_type: str,
        name: str,
        position: Tuple[float, float] = (0, 0),
        properties: Dict[str, Any] = None,
    ) -> Optional[WorkflowNode]:
        """Add a custom node"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        node_id = str(uuid.uuid4())[:8]

        node = WorkflowNode(
            id=node_id,
            type=NodeType(node_type),
            name=name,
            position=position,
            properties=properties or {},
            inputs=[NodePort(id=f"{node_id}_in", name="in", port_type=PortType.INPUT)],
            outputs=[
                NodePort(id=f"{node_id}_out", name="out", port_type=PortType.OUTPUT)
            ],
        )

        workflow.nodes.append(node)
        workflow.updated_at = time.time()
        self._save_workflow(workflow)

        return node

    def connect_nodes(
        self,
        workflow_id: str,
        source_node_id: str,
        source_port_id: str,
        target_node_id: str,
        target_port_id: str,
    ) -> Optional[NodeConnection]:
        """Connect two nodes"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        connection_id = str(uuid.uuid4())[:8]

        connection = NodeConnection(
            id=connection_id,
            source_node_id=source_node_id,
            source_port_id=source_port_id,
            target_node_id=target_node_id,
            target_port_id=target_port_id,
        )

        workflow.connections.append(connection)
        workflow.updated_at = time.time()
        self._save_workflow(workflow)

        return connection

    def remove_node(self, workflow_id: str, node_id: str) -> bool:
        """Remove a node"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.nodes = [n for n in workflow.nodes if n.id != node_id]
        workflow.connections = [
            c
            for c in workflow.connections
            if c.source_node_id != node_id and c.target_node_id != node_id
        ]

        workflow.updated_at = time.time()
        self._save_workflow(workflow)

        return True

    def remove_connection(self, workflow_id: str, connection_id: str) -> bool:
        """Remove a connection"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.connections = [
            c for c in workflow.connections if c.id != connection_id
        ]
        workflow.updated_at = time.time()
        self._save_workflow(workflow)

        return True

    def update_node_properties(
        self,
        workflow_id: str,
        node_id: str,
        properties: Dict[str, Any],
    ) -> bool:
        """Update node properties"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        for node in workflow.nodes:
            if node.id == node_id:
                node.properties.update(properties)
                workflow.updated_at = time.time()
                self._save_workflow(workflow)
                return True

        return False

    def update_node_position(
        self,
        workflow_id: str,
        node_id: str,
        position: Tuple[float, float],
    ) -> bool:
        """Update node position"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        for node in workflow.nodes:
            if node.id == node_id:
                node.position = position
                workflow.updated_at = time.time()
                self._save_workflow(workflow)
                return True

        return False

    def get_workflow(self, workflow_id: str) -> Optional[VisualWorkflow]:
        """Get workflow by ID"""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows"""
        return [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "node_count": len(w.nodes),
                "updated_at": w.updated_at,
            }
            for w in self._workflows.values()
        ]

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        if workflow_id not in self._workflows:
            return False

        del self._workflows[workflow_id]

        workflow_file = self.save_dir / f"{workflow_id}.json"
        if workflow_file.exists():
            workflow_file.unlink()

        return True

    def duplicate_workflow(
        self, workflow_id: str, new_name: str = None
    ) -> Optional[VisualWorkflow]:
        """Duplicate a workflow"""
        original = self._workflows.get(workflow_id)
        if not original:
            return None

        new_workflow = VisualWorkflow(
            id=str(uuid.uuid4())[:8],
            name=new_name or f"{original.name} (copy)",
            description=original.description,
            nodes=[WorkflowNode.from_dict(n.to_dict()) for n in original.nodes],
            connections=[
                NodeConnection.from_dict(c.to_dict()) for c in original.connections
            ],
            variables=dict(original.variables),
            settings=dict(original.settings),
        )

        for node in new_workflow.nodes:
            node.position = (node.position[0] + 50, node.position[1] + 50)

        self._workflows[new_workflow.id] = new_workflow
        self._save_workflow(new_workflow)

        return new_workflow

    def export_workflow(self, workflow_id: str) -> str:
        """Export workflow as JSON"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return ""

        return json.dumps(workflow.to_dict(), indent=2)

    def import_workflow(self, json_data: str) -> Optional[VisualWorkflow]:
        """Import workflow from JSON"""
        try:
            data = json.loads(json_data)
            workflow = VisualWorkflow.from_dict(data)

            workflow.id = str(uuid.uuid4())[:8]

            self._workflows[workflow.id] = workflow
            self._save_workflow(workflow)

            return workflow
        except Exception as e:
            self.logger.error(f"Import error: {e}")
            return None

    def validate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Validate workflow structure"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return {"valid": False, "errors": ["Workflow not found"]}

        errors = []
        warnings = []

        if not workflow.nodes:
            errors.append("Workflow has no nodes")

        trigger_nodes = [n for n in workflow.nodes if n.type == NodeType.TRIGGER]
        if len(trigger_nodes) == 0:
            warnings.append("No trigger node found")
        elif len(trigger_nodes) > 1:
            warnings.append("Multiple trigger nodes found")

        for node in workflow.nodes:
            has_input = any(c.target_node_id == node.id for c in workflow.connections)

            if node.type != NodeType.TRIGGER and not has_input:
                warnings.append(f"Node '{node.name}' has no input connection")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def get_node_templates(self) -> List[Dict[str, Any]]:
        """Get available node templates"""
        return NodeTemplate.list_templates()
