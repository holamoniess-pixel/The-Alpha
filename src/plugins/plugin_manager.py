#!/usr/bin/env python3
"""
ALPHA OMEGA - PLUGIN ARCHITECTURE
Third-party plugin system with sandboxing
Version: 2.0.0
"""

import asyncio
import json
import logging
import importlib
import sys
import time
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import subprocess
import zipfile
import tempfile
import shutil


class PluginStatus(Enum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UPDATING = "updating"


class PluginPermission(Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK = "network"
    SYSTEM = "system"
    UI = "ui"
    VOICE = "voice"
    AUTOMATION = "automation"
    MEMORY = "memory"
    LLM = "llm"


@dataclass
class PluginMetadata:
    id: str
    name: str
    version: str
    author: str
    description: str
    homepage: str = ""
    repository: str = ""
    license: str = "MIT"
    min_alpha_version: str = "2.0.0"
    max_alpha_version: str = ""
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    screenshots: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "homepage": self.homepage,
            "repository": self.repository,
            "license": self.license,
            "min_alpha_version": self.min_alpha_version,
            "max_alpha_version": self.max_alpha_version,
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "tags": self.tags,
            "icon": self.icon,
            "screenshots": self.screenshots,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginMetadata":
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            author=data.get("author", "unknown"),
            description=data.get("description", ""),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            license=data.get("license", "MIT"),
            min_alpha_version=data.get("min_alpha_version", "2.0.0"),
            max_alpha_version=data.get("max_alpha_version", ""),
            dependencies=data.get("dependencies", []),
            permissions=data.get("permissions", []),
            tags=data.get("tags", []),
            icon=data.get("icon", ""),
            screenshots=data.get("screenshots", []),
        )


@dataclass
class Plugin:
    metadata: PluginMetadata
    path: Path
    status: PluginStatus = PluginStatus.INSTALLED
    installed_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    enabled: bool = False
    error: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "path": str(self.path),
            "status": self.status.value,
            "installed_at": self.installed_at,
            "updated_at": self.updated_at,
            "enabled": self.enabled,
            "error": self.error,
            "config": self.config,
        }


@dataclass
class PluginContext:
    plugin_id: str
    data_dir: Path
    config: Dict[str, Any]
    permissions: List[str]

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or "*" in self.permissions


class PluginSandbox:
    """Sandboxed execution environment for plugins"""

    def __init__(self, plugin: Plugin):
        self.plugin = plugin
        self.logger = logging.getLogger(f"PluginSandbox-{plugin.metadata.id}")

    def create_context(self) -> PluginContext:
        """Create execution context for plugin"""
        return PluginContext(
            plugin_id=self.plugin.metadata.id,
            data_dir=self.plugin.path / "data",
            config=self.plugin.config,
            permissions=self.plugin.metadata.permissions,
        )

    def check_permission(self, permission: str) -> bool:
        """Check if plugin has permission"""
        return (
            permission in self.plugin.metadata.permissions
            or "*" in self.plugin.metadata.permissions
        )

    def validate_path_access(self, path: Path, write: bool = False) -> bool:
        """Validate path access"""
        if not self.check_permission("file_read"):
            return False
        if write and not self.check_permission("file_write"):
            return False

        plugin_data = self.plugin.path / "data"
        try:
            path.resolve().relative_to(plugin_data.resolve())
            return True
        except ValueError:
            return self.check_permission("system")


class PluginBase:
    """Base class for all plugins"""

    def __init__(self, context: PluginContext):
        self.context = context
        self.plugin_id = context.plugin_id
        self.data_dir = context.data_dir
        self.config = context.config
        self.logger = logging.getLogger(f"Plugin-{self.plugin_id}")

        self._hooks: Dict[str, List[Callable]] = {}
        self._commands: Dict[str, Callable] = {}

    async def initialize(self) -> bool:
        """Initialize plugin - override in subclass"""
        return True

    async def shutdown(self):
        """Shutdown plugin - override in subclass"""
        pass

    def register_hook(self, hook_name: str, callback: Callable):
        """Register a hook callback"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)

    def register_command(self, command_name: str, callback: Callable):
        """Register a command"""
        self._commands[command_name] = callback

    def get_hooks(self) -> Dict[str, List[Callable]]:
        return self._hooks

    def get_commands(self) -> Dict[str, Callable]:
        return self._commands


class PluginManager:
    """Manages plugin lifecycle"""

    PLUGIN_DIR = Path("plugins")

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("PluginManager")

        self.PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

        self._plugins: Dict[str, Plugin] = {}
        self._instances: Dict[str, PluginBase] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._commands: Dict[str, Callable] = {}

        self._db_path = Path("data/plugins.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()

        self._init_db()

    def _init_db(self):
        """Initialize plugin database"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plugins (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    installed_at REAL,
                    updated_at REAL
                )
            """)
            conn.commit()

    async def initialize(self) -> bool:
        """Initialize plugin manager"""
        self.logger.info("Initializing Plugin Manager...")

        await self._load_installed_plugins()

        self.logger.info(f"Plugin Manager initialized. {len(self._plugins)} plugins")
        return True

    async def _load_installed_plugins(self):
        """Load installed plugins"""
        for plugin_dir in self.PLUGIN_DIR.iterdir():
            if plugin_dir.is_dir():
                manifest_path = plugin_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        await self._load_plugin(plugin_dir)
                    except Exception as e:
                        self.logger.error(
                            f"Failed to load plugin {plugin_dir.name}: {e}"
                        )

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("SELECT id, data FROM plugins")
            for row in cursor.fetchall():
                if row[0] not in self._plugins:
                    plugin_data = json.loads(row[1])
                    metadata = PluginMetadata.from_dict(plugin_data.get("metadata", {}))
                    path = Path(plugin_data.get("path", ""))

                    if path.exists():
                        plugin = Plugin(
                            metadata=metadata,
                            path=path,
                            status=PluginStatus(plugin_data.get("status", "installed")),
                            installed_at=plugin_data.get("installed_at", time.time()),
                            updated_at=plugin_data.get("updated_at", time.time()),
                            enabled=plugin_data.get("enabled", False),
                            config=plugin_data.get("config", {}),
                        )
                        self._plugins[metadata.id] = plugin

    async def _load_plugin(self, plugin_path: Path) -> Optional[Plugin]:
        """Load a plugin from directory"""
        manifest_path = plugin_path / "manifest.json"

        if not manifest_path.exists():
            return None

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        metadata = PluginMetadata.from_dict(manifest_data)

        plugin = Plugin(
            metadata=metadata,
            path=plugin_path,
        )

        self._plugins[metadata.id] = plugin

        return plugin

    async def install_plugin(self, source: str) -> Optional[Plugin]:
        """Install a plugin from source (path, zip, or URL)"""
        self.logger.info(f"Installing plugin from: {source}")

        source_path = Path(source)

        if (
            source_path.exists()
            and source_path.is_file()
            and source_path.suffix == ".zip"
        ):
            return await self._install_from_zip(source_path)

        elif source_path.exists() and source_path.is_dir():
            return await self._install_from_directory(source_path)

        elif source.startswith(("http://", "https://")):
            return await self._install_from_url(source)

        else:
            self.logger.error(f"Unknown plugin source: {source}")
            return None

    async def _install_from_zip(self, zip_path: Path) -> Optional[Plugin]:
        """Install plugin from zip file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)

            extracted_path = Path(temp_dir)
            plugin_dirs = [p for p in extracted_path.iterdir() if p.is_dir()]

            if not plugin_dirs:
                return None

            plugin_dir = plugin_dirs[0]
            return await self._install_from_directory(plugin_dir)

    async def _install_from_directory(self, source_dir: Path) -> Optional[Plugin]:
        """Install plugin from directory"""
        manifest_path = source_dir / "manifest.json"

        if not manifest_path.exists():
            self.logger.error("No manifest.json found")
            return None

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        metadata = PluginMetadata.from_dict(manifest_data)

        dest_dir = self.PLUGIN_DIR / metadata.id
        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        shutil.copytree(source_dir, dest_dir)

        plugin = Plugin(
            metadata=metadata,
            path=dest_dir,
            installed_at=time.time(),
        )

        self._plugins[metadata.id] = plugin
        self._save_plugin(plugin)

        self.logger.info(f"Plugin installed: {metadata.name} v{metadata.version}")
        return plugin

    async def _install_from_url(self, url: str) -> Optional[Plugin]:
        """Install plugin from URL"""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(url)

                if response.status_code != 200:
                    return None

                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
                    f.write(response.content)
                    temp_path = Path(f.name)

                result = await self._install_from_zip(temp_path)
                temp_path.unlink()

                return result

        except Exception as e:
            self.logger.error(f"Failed to download plugin: {e}")
            return None

    def _save_plugin(self, plugin: Plugin):
        """Save plugin to database"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO plugins (id, data, installed_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    plugin.metadata.id,
                    json.dumps(plugin.to_dict()),
                    plugin.installed_at,
                    plugin.updated_at,
                ),
            )
            conn.commit()

    async def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin"""
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]

        if plugin.enabled:
            return True

        try:
            instance = await self._create_plugin_instance(plugin)

            if instance:
                success = await instance.initialize()

                if success:
                    self._instances[plugin_id] = instance
                    plugin.enabled = True
                    plugin.status = PluginStatus.ENABLED
                    plugin.updated_at = time.time()

                    for hook_name, callbacks in instance.get_hooks().items():
                        if hook_name not in self._hooks:
                            self._hooks[hook_name] = []
                        self._hooks[hook_name].extend(callbacks)

                    self._commands.update(instance.get_commands())

                    self._save_plugin(plugin)
                    self.logger.info(f"Plugin enabled: {plugin.metadata.name}")
                    return True

        except Exception as e:
            plugin.status = PluginStatus.ERROR
            plugin.error = str(e)
            self.logger.error(f"Failed to enable plugin: {e}")

        return False

    async def _create_plugin_instance(self, plugin: Plugin) -> Optional[PluginBase]:
        """Create plugin instance"""
        main_file = plugin.path / "main.py"

        if not main_file.exists():
            return None

        module_name = f"plugin_{plugin.metadata.id}"

        spec = importlib.util.spec_from_file_location(module_name, main_file)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = spec.loader.exec_module(module)

        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, PluginBase)
                and obj != PluginBase
            ):
                context = PluginContext(
                    plugin_id=plugin.metadata.id,
                    data_dir=plugin.path / "data",
                    config=plugin.config,
                    permissions=plugin.metadata.permissions,
                )
                return obj(context)

        return None

    async def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin"""
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]

        if not plugin.enabled:
            return True

        if plugin_id in self._instances:
            instance = self._instances[plugin_id]
            await instance.shutdown()

            for hook_name, callbacks in instance.get_hooks().items():
                if hook_name in self._hooks:
                    self._hooks[hook_name] = [
                        c for c in self._hooks[hook_name] if c not in callbacks
                    ]

            for cmd_name in instance.get_commands():
                if cmd_name in self._commands:
                    del self._commands[cmd_name]

            del self._instances[plugin_id]

        plugin.enabled = False
        plugin.status = PluginStatus.DISABLED
        plugin.updated_at = time.time()

        self._save_plugin(plugin)
        self.logger.info(f"Plugin disabled: {plugin.metadata.name}")
        return True

    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a plugin"""
        if plugin_id not in self._plugins:
            return False

        await self.disable_plugin(plugin_id)

        plugin = self._plugins[plugin_id]

        if plugin.path.exists():
            shutil.rmtree(plugin.path)

        del self._plugins[plugin_id]

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM plugins WHERE id = ?", (plugin_id,))
            conn.commit()

        self.logger.info(f"Plugin uninstalled: {plugin.metadata.name}")
        return True

    async def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Execute all callbacks for a hook"""
        results = []

        if hook_name in self._hooks:
            for callback in self._hooks[hook_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        result = await callback(*args, **kwargs)
                    else:
                        result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Hook error: {e}")

        return results

    async def execute_command(self, command_name: str, *args, **kwargs) -> Any:
        """Execute a registered command"""
        if command_name in self._commands:
            callback = self._commands[command_name]
            try:
                if asyncio.iscoroutinefunction(callback):
                    return await callback(*args, **kwargs)
                else:
                    return callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Command error: {e}")

        return None

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get plugin by ID"""
        return self._plugins.get(plugin_id)

    def list_plugins(self, status: PluginStatus = None) -> List[Plugin]:
        """List all plugins"""
        plugins = list(self._plugins.values())

        if status:
            plugins = [p for p in plugins if p.status == status]

        return plugins

    def get_plugin_config(self, plugin_id: str) -> Dict[str, Any]:
        """Get plugin configuration"""
        plugin = self.get_plugin(plugin_id)
        return plugin.config if plugin else {}

    def update_plugin_config(self, plugin_id: str, config: Dict[str, Any]):
        """Update plugin configuration"""
        plugin = self.get_plugin(plugin_id)
        if plugin:
            plugin.config.update(config)
            plugin.updated_at = time.time()
            self._save_plugin(plugin)

    def create_plugin_template(self, name: str, output_dir: Path = None) -> Path:
        """Create a new plugin template"""
        plugin_id = name.lower().replace(" ", "_").replace("-", "_")
        plugin_dir = output_dir or self.PLUGIN_DIR / plugin_id
        plugin_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "id": plugin_id,
            "name": name,
            "version": "1.0.0",
            "author": "Your Name",
            "description": f"{name} plugin for Alpha Omega",
            "permissions": ["file_read"],
            "dependencies": [],
            "tags": [],
        }

        with open(plugin_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        main_code = f'''#!/usr/bin/env python3
"""{name} Plugin"""

from src.plugins.plugin_manager import PluginBase, PluginContext


class {name.replace(" ", "").replace("_", "")}Plugin(PluginBase):
    def __init__(self, context: PluginContext):
        super().__init__(context)
    
    async def initialize(self) -> bool:
        self.logger.info("{name} plugin initialized")
        
        self.register_command("{plugin_id}_hello", self.hello)
        
        return True
    
    async def hello(self, name: str = "World") -> str:
        return f"Hello, {{name}}! From {name} plugin."
    
    async def shutdown(self):
        self.logger.info("{name} plugin shutting down")
'''

        with open(plugin_dir / "main.py", "w") as f:
            f.write(main_code)

        (plugin_dir / "data").mkdir(exist_ok=True)

        self.logger.info(f"Created plugin template: {plugin_dir}")
        return plugin_dir

    def get_stats(self) -> Dict[str, Any]:
        """Get plugin manager statistics"""
        return {
            "total_plugins": len(self._plugins),
            "enabled_plugins": sum(1 for p in self._plugins.values() if p.enabled),
            "disabled_plugins": sum(1 for p in self._plugins.values() if not p.enabled),
            "registered_hooks": len(self._hooks),
            "registered_commands": len(self._commands),
        }
