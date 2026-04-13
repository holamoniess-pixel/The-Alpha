"""
ALPHA OMEGA - Settings API Routes
RESTful Endpoints for Configuration Management
Version: 2.0.0
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("SettingsRoutes")

router = APIRouter(prefix="/settings", tags=["settings"])

config_manager = None


def get_config_manager():
    global config_manager
    if config_manager is None:
        from src.core.config_manager import ConfigManager

        config_manager = ConfigManager()
    return config_manager


class SettingUpdate(BaseModel):
    value: Any


class CategoryUpdate(BaseModel):
    settings: Dict[str, Any]


class ConfigImport(BaseModel):
    config: str
    merge: bool = True


@router.get("/")
async def get_all_settings():
    """Get all settings organized by category"""
    manager = get_config_manager()
    return {
        category: manager.get_category(category)
        for category in manager.get_all_schemas().keys()
    }


@router.get("/{category}")
async def get_category_settings(category: str):
    """Get all settings for a specific category"""
    manager = get_config_manager()

    if category not in manager.get_all_schemas():
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    return manager.get_category(category)


@router.post("/{category}")
async def update_category_settings(category: str, update: CategoryUpdate):
    """Update multiple settings in a category"""
    manager = get_config_manager()

    if category not in manager.get_all_schemas():
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    success = manager.set_category(category, update.settings)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update settings")

    return {"success": True, "message": f"Updated {len(update.settings)} settings"}


@router.get("/{category}/{key}")
async def get_single_setting(category: str, key: str):
    """Get a single setting value"""
    manager = get_config_manager()

    full_key = f"{category}.{key}"
    value = manager.get(full_key)

    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{full_key}' not found")

    return {"key": full_key, "value": value}


@router.put("/{category}/{key}")
async def update_single_setting(category: str, key: str, update: SettingUpdate):
    """Update a single setting"""
    manager = get_config_manager()

    schema = manager.get_category_schema(category)
    setting_def = next((s for s in schema if s["key"] == key), None)

    if not setting_def:
        raise HTTPException(
            status_code=404, detail=f"Setting '{key}' not found in '{category}'"
        )

    full_key = f"{category}.{key}"
    success = manager.set(
        full_key, update.value, sensitive=setting_def.get("sensitive", False)
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to update setting")

    manager._save_config()

    return {
        "success": True,
        "key": full_key,
        "value": update.value,
        "requires_restart": setting_def.get("requires_restart", False),
    }


@router.get("/schema/{category}")
async def get_category_schema(category: str):
    """Get the schema definition for a category"""
    manager = get_config_manager()

    schema = manager.get_category_schema(category)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    return {"category": category, "settings": schema}


@router.get("/schema")
async def get_all_schemas():
    """Get all category schemas"""
    manager = get_config_manager()
    return {"schemas": manager.get_all_schemas()}


@router.post("/validate")
async def validate_settings(config: Dict[str, Any] = None):
    """Validate settings without saving"""
    manager = get_config_manager()
    result = manager.validate_config(config)
    return result.to_dict()


@router.post("/reset/{category}")
async def reset_category(category: str):
    """Reset a category to defaults"""
    manager = get_config_manager()

    if category not in manager.get_all_schemas():
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    success = manager.reset_category(category)
    return {"success": success, "message": f"Category '{category}' reset to defaults"}


@router.post("/reset-all")
async def reset_all_settings():
    """Reset all settings to defaults"""
    manager = get_config_manager()
    success = manager.reset_all()
    return {"success": success, "message": "All settings reset to defaults"}


@router.get("/export")
async def export_settings():
    """Export current configuration"""
    manager = get_config_manager()
    return {"config": manager.export_config()}


@router.post("/import")
async def import_settings(import_data: ConfigImport):
    """Import configuration"""
    manager = get_config_manager()
    success = manager.import_config(import_data.config, import_data.merge)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to import configuration")

    return {"success": True, "message": "Configuration imported successfully"}


@router.post("/api-keys")
async def set_api_key(provider: str, api_key: str):
    """Set an API key (stored encrypted in vault)"""
    manager = get_config_manager()

    provider_map = {
        "openai": "intelligence.openai_api_key",
        "anthropic": "intelligence.anthropic_api_key",
        "google": "intelligence.google_api_key",
        "groq": "intelligence.groq_api_key",
        "openrouter": "intelligence.openrouter_api_key",
    }

    if provider not in provider_map:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    key_path = provider_map[provider]
    success = manager.set(key_path, api_key, sensitive=True)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to store API key")

    manager._save_config()

    return {"success": True, "message": f"{provider} API key stored securely"}


@router.delete("/api-keys/{provider}")
async def delete_api_key(provider: str):
    """Delete an API key"""
    manager = get_config_manager()

    provider_map = {
        "openai": "intelligence.openai_api_key",
        "anthropic": "intelligence.anthropic_api_key",
        "google": "intelligence.google_api_key",
        "groq": "intelligence.groq_api_key",
        "openrouter": "intelligence.openrouter_api_key",
    }

    if provider not in provider_map:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    key_path = provider_map[provider]
    success = manager.set(key_path, "")

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete API key")

    manager._save_config()

    return {"success": True, "message": f"{provider} API key deleted"}


@router.get("/api-keys/status")
async def get_api_keys_status():
    """Get status of all configured API keys (without revealing values)"""
    manager = get_config_manager()

    providers = ["openai", "anthropic", "google", "groq", "openrouter"]
    provider_map = {
        "openai": "intelligence.openai_api_key",
        "anthropic": "intelligence.anthropic_api_key",
        "google": "intelligence.google_api_key",
        "groq": "intelligence.groq_api_key",
        "openrouter": "intelligence.openrouter_api_key",
    }

    status = {}
    for provider in providers:
        key_path = provider_map[provider]
        value = manager.get(key_path)
        status[provider] = {
            "configured": bool(value and value != ""),
            "key_length": len(value) if value else 0,
        }

    return {"api_keys": status}


@router.get("/categories")
async def list_categories():
    """List all available setting categories"""
    manager = get_config_manager()
    schemas = manager.get_all_schemas()

    categories = []
    for name in schemas.keys():
        settings = schemas[name]
        categories.append(
            {
                "name": name,
                "display_name": name.replace("_", " ").title(),
                "settings_count": len(settings),
            }
        )

    return {"categories": categories}
