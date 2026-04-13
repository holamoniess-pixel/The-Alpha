#!/usr/bin/env python3
"""
ALPHA OMEGA - SELF-EXTENSION ENGINE
AI that can create its own tools and features on demand
Version: 2.0.0
"""

import asyncio
import logging
import time
import json
import os
import sys
import subprocess
import importlib
import inspect
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
import textwrap


class TaskComplexity(Enum):
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    VERY_COMPLEX = 4


class TaskStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    CROSSCHECKING = "crosschecking"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Task:
    task_id: str
    description: str
    complexity: TaskComplexity
    status: TaskStatus = TaskStatus.PENDING
    sub_tasks: List["Task"] = field(default_factory=list)
    plan: List[Dict[str, Any]] = field(default_factory=list)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    retries: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    tool_used: Optional[str] = None
    new_tool_created: bool = False


@dataclass
class Tool:
    tool_id: str
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    code: Optional[str] = None
    function: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    is_builtin: bool = True
    success_rate: float = 1.0
    usage_count: int = 0


class ToolRegistry:
    """Registry of all available tools - both builtin and dynamically created"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.categories: Dict[str, List[str]] = {}
        self.logger = logging.getLogger("ToolRegistry")
        self._init_builtin_tools()

    def _init_builtin_tools(self):
        """Initialize all builtin tools"""
        builtin_tools = [
            Tool(
                tool_id="open_app",
                name="Open Application",
                description="Open any application by name or path",
                category="application",
                parameters={"app": "string", "path": "string (optional)"},
            ),
            Tool(
                tool_id="close_app",
                name="Close Application",
                description="Close a running application",
                category="application",
                parameters={"app": "string"},
            ),
            Tool(
                tool_id="type_text",
                name="Type Text",
                description="Type text into active window",
                category="input",
                parameters={"text": "string", "interval": "float (optional)"},
            ),
            Tool(
                tool_id="click_position",
                name="Click Position",
                description="Click at specific screen coordinates",
                category="input",
                parameters={"x": "int", "y": "int", "button": "string (left/right)"},
            ),
            Tool(
                tool_id="press_key",
                name="Press Key",
                description="Press a keyboard key",
                category="input",
                parameters={"key": "string", "modifiers": "list (optional)"},
            ),
            Tool(
                tool_id="screenshot",
                name="Screenshot",
                description="Capture screen or region",
                category="vision",
                parameters={"region": "tuple (optional)"},
            ),
            Tool(
                tool_id="search_web",
                name="Web Search",
                description="Search the web",
                category="web",
                parameters={"query": "string", "engine": "string (optional)"},
            ),
            Tool(
                tool_id="open_url",
                name="Open URL",
                description="Open URL in browser",
                category="web",
                parameters={"url": "string"},
            ),
            Tool(
                tool_id="file_create",
                name="Create File",
                description="Create a new file",
                category="file",
                parameters={"path": "string", "content": "string"},
            ),
            Tool(
                tool_id="file_read",
                name="Read File",
                description="Read file contents",
                category="file",
                parameters={"path": "string"},
            ),
            Tool(
                tool_id="file_delete",
                name="Delete File",
                description="Delete a file",
                category="file",
                parameters={"path": "string"},
            ),
            Tool(
                tool_id="run_shell",
                name="Shell Command",
                description="Execute shell command",
                category="system",
                parameters={"command": "string", "timeout": "int (optional)"},
            ),
            Tool(
                tool_id="volume_set",
                name="Set Volume",
                description="Set system volume",
                category="audio",
                parameters={"level": "int (0-100)"},
            ),
            Tool(
                tool_id="window_activate",
                name="Activate Window",
                description="Bring window to foreground",
                category="window",
                parameters={"title": "string"},
            ),
            Tool(
                tool_id="wait",
                name="Wait",
                description="Wait for specified duration",
                category="control",
                parameters={"seconds": "float"},
            ),
            Tool(
                tool_id="find_on_screen",
                name="Find On Screen",
                description="Find image or text on screen",
                category="vision",
                parameters={"target": "string", "confidence": "float (optional)"},
            ),
        ]

        for tool in builtin_tools:
            self.register_tool(tool)

    def register_tool(self, tool: Tool):
        """Register a new tool"""
        self.tools[tool.tool_id] = tool

        if tool.category not in self.categories:
            self.categories[tool.category] = []
        self.categories[tool.category].append(tool.tool_id)

        self.logger.info(f"Registered tool: {tool.name} ({tool.tool_id})")

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get tool by ID"""
        return self.tools.get(tool_id)

    def find_tools_for_task(self, task_description: str) -> List[Tool]:
        """Find relevant tools for a task"""
        task_lower = task_description.lower()
        relevant = []

        for tool in self.tools.values():
            if any(kw in task_lower for kw in tool.name.lower().split()):
                relevant.append(tool)
            elif any(kw in task_lower for kw in tool.category.lower().split()):
                relevant.append(tool)

        return relevant

    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a category"""
        tool_ids = self.categories.get(category, [])
        return [self.tools[tid] for tid in tool_ids]

    def list_all_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        return [
            {
                "id": t.tool_id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "parameters": t.parameters,
                "is_builtin": t.is_builtin,
                "success_rate": t.success_rate,
            }
            for t in self.tools.values()
        ]


class TaskPlanner:
    """Plans task execution using 4-step process"""

    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry
        self.logger = logging.getLogger("TaskPlanner")

    def analyze_task(self, description: str) -> Task:
        """Analyze and create a task from description"""
        task_id = hashlib.md5(f"{description}{time.time()}".encode()).hexdigest()[:12]

        complexity = self._assess_complexity(description)

        task = Task(task_id=task_id, description=description, complexity=complexity)

        return task

    def _assess_complexity(self, description: str) -> TaskComplexity:
        """Assess task complexity"""
        desc_lower = description.lower()

        complex_indicators = [
            "and then",
            "after that",
            "also",
            "multiple",
            "all",
            "each",
        ]
        moderate_indicators = ["open", "find", "search", "send", "create"]

        complex_count = sum(1 for ind in complex_indicators if ind in desc_lower)

        if complex_count >= 3:
            return TaskComplexity.VERY_COMPLEX
        elif complex_count >= 2:
            return TaskComplexity.COMPLEX
        elif complex_count >= 1 or len(description.split()) > 15:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.SIMPLE

    def create_plan(self, task: Task) -> List[Dict[str, Any]]:
        """Create execution plan for task"""
        plan = []
        description = task.description.lower()

        if task.complexity == TaskComplexity.SIMPLE:
            plan = self._plan_simple(task.description)
        elif task.complexity == TaskComplexity.MODERATE:
            plan = self._plan_moderate(task.description)
        else:
            plan = self._plan_complex(task.description)

        task.plan = plan
        return plan

    def _plan_simple(self, description: str) -> List[Dict[str, Any]]:
        """Plan for simple tasks"""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["open", "start", "launch"]):
            app_match = re.search(r"(?:open|start|launch)\s+(\w+)", desc_lower)
            if app_match:
                return [{"tool": "open_app", "params": {"app": app_match.group(1)}}]

        if any(kw in desc_lower for kw in ["type", "write"]):
            text_match = re.search(
                r'(?:type|write)\s+[\'"]?(.+?)[\'"]?(?:\s|$)', desc_lower
            )
            if text_match:
                return [{"tool": "type_text", "params": {"text": text_match.group(1)}}]

        if "screenshot" in desc_lower:
            return [{"tool": "screenshot", "params": {}}]

        if any(kw in desc_lower for kw in ["search", "find"]):
            query_match = re.search(r"(?:search|find)\s+(?:for\s+)?(.+)", desc_lower)
            if query_match:
                return [
                    {"tool": "search_web", "params": {"query": query_match.group(1)}}
                ]

        return [{"tool": "unknown", "params": {}, "description": description}]

    def _plan_moderate(self, description: str) -> List[Dict[str, Any]]:
        """Plan for moderate tasks"""
        plan = []
        desc_lower = description.lower()

        if "spotify" in desc_lower:
            plan.append(
                {
                    "tool": "open_app",
                    "params": {"app": "spotify"},
                    "step": "Open Spotify",
                }
            )
            if "play" in desc_lower:
                plan.append(
                    {
                        "tool": "wait",
                        "params": {"seconds": 2},
                        "step": "Wait for app to load",
                    }
                )
                plan.append(
                    {
                        "tool": "press_key",
                        "params": {"key": "space"},
                        "step": "Play/Pause",
                    }
                )

        elif "whatsapp" in desc_lower:
            plan.append(
                {
                    "tool": "open_app",
                    "params": {"app": "whatsapp"},
                    "step": "Open WhatsApp",
                }
            )
            plan.append(
                {
                    "tool": "wait",
                    "params": {"seconds": 3},
                    "step": "Wait for app to load",
                }
            )

        else:
            simple_plan = self._plan_simple(description)
            if simple_plan[0]["tool"] != "unknown":
                plan = simple_plan
            else:
                plan.append(
                    {
                        "tool": "decompose",
                        "params": {},
                        "description": f"Need to decompose: {description}",
                    }
                )

        return plan

    def _plan_complex(self, description: str) -> List[Dict[str, Any]]:
        """Plan for complex tasks - decompose into sub-tasks"""
        plan = []
        desc_lower = description.lower()

        parts = re.split(r"\s+(?:and|then|after|also)\s+", desc_lower)

        for part in parts:
            sub_plan = self._plan_simple(part)
            if sub_plan[0]["tool"] != "unknown":
                plan.extend(sub_plan)
            else:
                plan.append(
                    {
                        "tool": "decompose",
                        "params": {"sub_task": part},
                        "description": part,
                    }
                )

        return plan

    def decompose_task(self, task: Task) -> List[Task]:
        """Decompose complex task into sub-tasks"""
        sub_tasks = []

        for i, step in enumerate(task.plan):
            if step.get("tool") == "decompose":
                sub_task = Task(
                    task_id=f"{task.task_id}_sub_{i}",
                    description=step.get("description", "Unknown sub-task"),
                    complexity=TaskComplexity.MODERATE,
                )
                sub_tasks.append(sub_task)

        task.sub_tasks = sub_tasks
        return sub_tasks


class ToolGenerator:
    """Generates new tools dynamically when needed"""

    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry
        self.logger = logging.getLogger("ToolGenerator")
        self.generated_tools_path = Path("data/generated_tools")
        self.generated_tools_path.mkdir(parents=True, exist_ok=True)

    async def generate_tool(
        self, requirement: str, context: Dict[str, Any] = None
    ) -> Optional[Tool]:
        """Generate a new tool based on requirement"""
        self.logger.info(f"Generating tool for: {requirement}")

        tool_spec = self._analyze_requirement(requirement)

        code = self._generate_code(tool_spec, context)

        if code:
            tool_id = f"gen_{hashlib.md5(requirement.encode()).hexdigest()[:8]}"

            tool = Tool(
                tool_id=tool_id,
                name=tool_spec["name"],
                description=tool_spec["description"],
                category=tool_spec["category"],
                parameters=tool_spec["parameters"],
                code=code,
                is_builtin=False,
            )

            success = await self._save_and_load_tool(tool)

            if success:
                self.registry.register_tool(tool)
                self.logger.info(f"Successfully generated tool: {tool.name}")
                return tool

        return None

    def _analyze_requirement(self, requirement: str) -> Dict[str, Any]:
        """Analyze requirement and create tool specification"""
        req_lower = requirement.lower()

        if "whatsapp" in req_lower and "message" in req_lower:
            return {
                "name": "WhatsApp Messenger",
                "description": "Send WhatsApp messages to contacts",
                "category": "messaging",
                "parameters": {"contact": "string", "message": "string"},
                "template": "whatsapp_message",
            }

        elif "email" in req_lower or "mail" in req_lower:
            return {
                "name": "Email Sender",
                "description": "Send emails",
                "category": "communication",
                "parameters": {"to": "string", "subject": "string", "body": "string"},
                "template": "email_sender",
            }

        elif "discord" in req_lower:
            return {
                "name": "Discord Integration",
                "description": "Interact with Discord",
                "category": "messaging",
                "parameters": {"channel": "string", "message": "string"},
                "template": "discord_integration",
            }

        else:
            return {
                "name": f"Custom Tool: {requirement[:30]}",
                "description": f"Generated tool for: {requirement}",
                "category": "custom",
                "parameters": {"input": "any"},
                "template": "generic",
            }

    def _generate_code(
        self, spec: Dict[str, Any], context: Dict[str, Any] = None
    ) -> str:
        """Generate Python code for the tool"""
        template = spec.get("template", "generic")

        if template == "whatsapp_message":
            return self._generate_whatsapp_code(spec)
        elif template == "email_sender":
            return self._generate_email_code(spec)
        elif template == "discord_integration":
            return self._generate_discord_code(spec)
        else:
            return self._generate_generic_code(spec)

    def _generate_whatsapp_code(self, spec: Dict[str, Any]) -> str:
        return textwrap.dedent('''
import pyautogui
import time
import subprocess

async def execute(contact: str, message: str) -> dict:
    """Send WhatsApp message"""
    try:
        # Open WhatsApp
        subprocess.Popen(["cmd", "/c", "start", "whatsapp://"], shell=True)
        time.sleep(5)  # Wait for WhatsApp to open
        
        # Use Ctrl+F to search
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.5)
        
        # Type contact name
        pyautogui.write(contact)
        time.sleep(1)
        
        # Press Enter to select
        pyautogui.press('enter')
        time.sleep(1)
        
        # Type message
        pyautogui.write(message)
        time.sleep(0.5)
        
        # Send
        pyautogui.press('enter')
        
        return {"success": True, "message": f"Message sent to {contact}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
''')

    def _generate_email_code(self, spec: Dict[str, Any]) -> str:
        return textwrap.dedent('''
import subprocess
import time
import pyautogui

async def execute(to: str, subject: str, body: str) -> dict:
    """Send email via default mail client"""
    try:
        # Open mailto link
        mailto = f"mailto:{to}?subject={subject}&body={body}"
        subprocess.Popen(["cmd", "/c", "start", mailto], shell=True)
        time.sleep(3)
        
        # Press Ctrl+Enter to send (Outlook)
        pyautogui.hotkey('ctrl', 'enter')
        
        return {"success": True, "message": f"Email sent to {to}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
''')

    def _generate_discord_code(self, spec: Dict[str, Any]) -> str:
        return textwrap.dedent('''
import pyautogui
import time
import subprocess

async def execute(channel: str, message: str) -> dict:
    """Send Discord message"""
    try:
        # Open Discord
        subprocess.Popen(["cmd", "/c", "start", "discord://"], shell=True)
        time.sleep(5)
        
        # Use Ctrl+K to search channels
        pyautogui.hotkey('ctrl', 'k')
        time.sleep(0.5)
        
        # Type channel name
        pyautogui.write(channel)
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(1)
        
        # Type message
        pyautogui.write(message)
        pyautogui.press('enter')
        
        return {"success": True, "message": f"Message sent to {channel}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
''')

    def _generate_generic_code(self, spec: Dict[str, Any]) -> str:
        return textwrap.dedent(f'''
async def execute(**kwargs) -> dict:
    """Generated tool: {spec["name"]}"""
    try:
        # Generic implementation
        # This tool needs to be customized based on specific requirements
        return {{"success": True, "message": "Tool executed (placeholder)"}}
    except Exception as e:
        return {{"success": False, "error": str(e)}}
''')

    async def _save_and_load_tool(self, tool: Tool) -> bool:
        """Save tool code and make it loadable"""
        try:
            file_path = self.generated_tools_path / f"{tool.tool_id}.py"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f'"""Auto-generated tool: {tool.name}"""\n\n')
                f.write(tool.code)

            return True
        except Exception as e:
            self.logger.error(f"Failed to save tool: {e}")
            return False


class FourStepExecutor:
    """Executes tasks using 4-step process: Plan → Implement → CrossCheck → Proceed"""

    def __init__(self, tool_registry: ToolRegistry, automation_engine=None):
        self.registry = tool_registry
        self.automation = automation_engine
        self.tool_generator = ToolGenerator(tool_registry)
        self.logger = logging.getLogger("FourStepExecutor")

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute task using 4-step process"""
        task.status = TaskStatus.PLANNING
        task.started_at = time.time()

        self.logger.info(f"[PLAN] Starting task: {task.description}")

        # STEP 1: PLAN
        plan_result = await self._step_plan(task)
        if not plan_result["success"]:
            return await self._handle_failure(task, plan_result.get("error"))

        # STEP 2: IMPLEMENT
        task.status = TaskStatus.IMPLEMENTING
        self.logger.info(f"[IMPLEMENT] Executing plan for task: {task.task_id}")

        impl_result = await self._step_implement(task)
        if not impl_result["success"]:
            return await self._handle_failure(task, impl_result.get("error"))

        # STEP 3: CROSS-CHECK
        task.status = TaskStatus.CROSSCHECKING
        self.logger.info(f"[CROSSCHECK] Verifying task completion: {task.task_id}")

        check_result = await self._step_crosscheck(task, impl_result)
        if not check_result["success"]:
            self.logger.warning(f"[CROSSCHECK] Verification failed, retrying...")
            return await self._handle_failure(task, check_result.get("error"))

        # STEP 4: PROCEED
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = impl_result

        duration = task.completed_at - task.started_at
        self.logger.info(f"[PROCEED] Task completed in {duration:.2f}s: {task.task_id}")

        return {
            "success": True,
            "task_id": task.task_id,
            "result": impl_result,
            "duration_seconds": duration,
            "retries": task.retries,
            "new_tool_created": task.new_tool_created,
        }

    async def _step_plan(self, task: Task) -> Dict[str, Any]:
        """Step 1: Plan the task execution"""
        try:
            # Check if we have tools for this task
            available_tools = self.registry.find_tools_for_task(task.description)

            if not available_tools:
                # Need to generate a new tool
                self.logger.info(f"[PLAN] No tool available, generating new one...")

                new_tool = await self.tool_generator.generate_tool(task.description)

                if new_tool:
                    task.new_tool_created = True
                    task.tool_used = new_tool.tool_id
                    available_tools = [new_tool]
                else:
                    return {
                        "success": False,
                        "error": "Could not generate tool for task",
                    }

            # Create execution plan
            task.plan = self._create_execution_plan(task, available_tools)

            return {"success": True, "plan": task.plan}

        except Exception as e:
            self.logger.error(f"[PLAN] Error: {e}")
            return {"success": False, "error": str(e)}

    async def _step_implement(self, task: Task) -> Dict[str, Any]:
        """Step 2: Implement the plan"""
        results = []

        for step in task.plan:
            step_result = await self._execute_step(step)
            results.append(step_result)

            task.execution_log.append(
                {"step": step, "result": step_result, "timestamp": time.time()}
            )

            if not step_result.get("success"):
                return {
                    "success": False,
                    "error": step_result.get("error"),
                    "partial_results": results,
                }

        return {"success": True, "results": results}

    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step"""
        tool_id = step.get("tool")
        params = step.get("params", {})

        tool = self.registry.get_tool(tool_id)

        if not tool:
            return {"success": False, "error": f"Tool not found: {tool_id}"}

        # Execute via automation engine if available
        if self.automation:
            try:
                result = await self.automation.execute_command(tool_id, params)
                return result.to_dict() if hasattr(result, "to_dict") else result
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Fallback: Try to execute tool's code directly
        if tool.code:
            try:
                exec_globals = {}
                exec(tool.code, exec_globals)

                if "execute" in exec_globals:
                    if asyncio.iscoroutinefunction(exec_globals["execute"]):
                        return await exec_globals["execute"](**params)
                    else:
                        return exec_globals["execute"](**params)
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "No execution method available"}

    async def _step_crosscheck(
        self, task: Task, impl_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 3: Cross-check that task was completed"""
        if not impl_result.get("success"):
            return {"success": False, "error": "Implementation failed"}

        # Check if results match expectations
        results = impl_result.get("results", [])

        failed_steps = [r for r in results if not r.get("success")]

        if failed_steps:
            return {"success": False, "error": f"{len(failed_steps)} steps failed"}

        return {"success": True}

    async def _handle_failure(self, task: Task, error: str) -> Dict[str, Any]:
        """Handle task failure with retry logic"""
        task.errors.append(error)
        task.retries += 1

        self.logger.warning(f"[RETRY] Task failed (attempt {task.retries}): {error}")

        if task.retries < task.max_retries:
            task.status = TaskStatus.RETRYING

            # Try alternative approach
            alternative = await self._find_alternative_approach(task)

            if alternative:
                self.logger.info(f"[RETRY] Trying alternative approach...")
                return await self.execute_task(task)

            return {"success": False, "error": error, "retries": task.retries}

        task.status = TaskStatus.FAILED
        return {
            "success": False,
            "task_id": task.task_id,
            "error": error,
            "retries": task.retries,
            "execution_log": task.execution_log,
        }

    async def _find_alternative_approach(self, task: Task) -> bool:
        """Find alternative way to complete the task"""
        # Try generating a new tool with different approach
        new_tool = await self.tool_generator.generate_tool(
            f"Alternative approach for: {task.description}",
            {"previous_errors": task.errors},
        )

        if new_tool:
            task.plan = [{"tool": new_tool.tool_id, "params": {}}]
            return True

        return False

    def _create_execution_plan(
        self, task: Task, tools: List[Tool]
    ) -> List[Dict[str, Any]]:
        """Create execution plan from available tools"""
        plan = []

        for tool in tools[:5]:  # Limit to 5 tools
            plan.append(
                {
                    "tool": tool.tool_id,
                    "params": self._extract_params(task.description, tool),
                    "description": tool.name,
                }
            )

        return plan

    def _extract_params(self, description: str, tool: Tool) -> Dict[str, Any]:
        """Extract parameters from description for a tool"""
        params = {}
        desc_lower = description.lower()

        for param_name, param_type in tool.parameters.items():
            if param_type == "string":
                # Try to extract value from description
                for word in desc_lower.split():
                    if len(word) > 2:
                        params[param_name] = word
                        break

        return params


class SelfExtensionEngine:
    """Main engine that orchestrates self-extension capabilities"""

    def __init__(
        self, automation_engine=None, intelligence_engine=None, memory_system=None
    ):
        self.automation = automation_engine
        self.intelligence = intelligence_engine
        self.memory = memory_system

        self.tool_registry = ToolRegistry()
        self.task_planner = TaskPlanner(self.tool_registry)
        self.executor = FourStepExecutor(self.tool_registry, automation_engine)

        self.logger = logging.getLogger("SelfExtensionEngine")
        self._stats = {
            "tasks_processed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tools_generated": 0,
            "retries_total": 0,
        }

    async def initialize(self) -> bool:
        """Initialize the self-extension engine"""
        self.logger.info("Initializing Self-Extension Engine...")

        self.logger.info(f"Loaded {len(self.tool_registry.tools)} builtin tools")

        self.logger.info("Self-Extension Engine initialized")
        return True

    async def process_request(
        self, description: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process a user request with full 4-step execution"""
        self.logger.info(f"Processing request: {description}")

        task = self.task_planner.analyze_task(description)
        self._stats["tasks_processed"] += 1

        result = await self.executor.execute_task(task)

        if result["success"]:
            self._stats["tasks_completed"] += 1
        else:
            self._stats["tasks_failed"] += 1

        self._stats["retries_total"] += result.get("retries", 0)

        if result.get("new_tool_created"):
            self._stats["tools_generated"] += 1

        return result

    def get_capabilities(self) -> Dict[str, Any]:
        """Get current system capabilities"""
        return {"tools": self.tool_registry.list_all_tools(), "stats": self._stats}

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return self._stats
