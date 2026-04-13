"""
ALPHA OMEGA - Skill Library
Storage and Export for Learned Skills
Version: 2.0.0
"""

import os
import sys
import time
import logging
import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("SkillLibrary")


@dataclass
class Skill:
    skill_id: str
    name: str
    description: str
    pattern_id: str
    script_content: str
    script_type: str
    created_at: float = field(default_factory=time.time)
    use_count: int = 0
    last_used: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    exported: bool = False
    favorite: bool = False
    cloud_synced: bool = False

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "pattern_id": self.pattern_id,
            "script_content": self.script_content,
            "script_type": self.script_type,
            "created_at": self.created_at,
            "use_count": self.use_count,
            "last_used": self.last_used,
            "tags": self.tags,
            "exported": self.exported,
            "favorite": self.favorite,
            "cloud_synced": self.cloud_synced,
        }


@dataclass
class ExportResult:
    success: bool
    output_path: str
    format: str
    error: Optional[str] = None


class SkillLibrary:
    def __init__(self, config: dict = None, library_dir: str = None):
        self.config = config or {}
        self.library_dir = Path(library_dir or "C:/AlphaOmega/skills")
        self.library_dir.mkdir(parents=True, exist_ok=True)

        self._scripts_dir = self.library_dir / "scripts"
        self._scripts_dir.mkdir(exist_ok=True)

        self._exports_dir = self.library_dir / "exports"
        self._exports_dir.mkdir(exist_ok=True)

        self._cloud_dir = self.config.get("cloud_dir")
        if self._cloud_dir:
            self._cloud_path = Path(self._cloud_dir)
            self._cloud_path.mkdir(parents=True, exist_ok=True)

        self._skills: Dict[str, Skill] = {}
        self._load_library()

    def _load_library(self):
        library_file = self.library_dir / "library.json"

        if library_file.exists():
            try:
                data = json.loads(library_file.read_text())
                for skill_data in data.get("skills", []):
                    skill = Skill(**skill_data)
                    self._skills[skill.skill_id] = skill
                logger.info(f"Loaded {len(self._skills)} skills from library")
            except Exception as e:
                logger.error(f"Failed to load library: {e}")

    def _save_library(self):
        library_file = self.library_dir / "library.json"
        try:
            data = {
                "skills": [s.to_dict() for s in self._skills.values()],
                "last_saved": time.time(),
            }
            library_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save library: {e}")

    def save_skill(self, skill: Skill) -> str:
        if not skill.skill_id:
            skill.skill_id = hashlib.md5(
                f"{skill.name}{time.time()}".encode()
            ).hexdigest()[:12]

        script_file = self._scripts_dir / f"{skill.skill_id}.{skill.script_type}"
        script_file.write_text(skill.script_content)

        self._skills[skill.skill_id] = skill
        self._save_library()

        logger.info(f"Saved skill: {skill.name} ({skill.skill_id})")
        return skill.skill_id

    def load_skill(self, skill_id: str) -> Optional[Skill]:
        if skill_id in self._skills:
            skill = self._skills[skill_id]

            script_file = self._scripts_dir / f"{skill_id}.{skill.script_type}"
            if script_file.exists():
                skill.script_content = script_file.read_text()

            return skill

        return None

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    def get_all_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def get_skills_by_tag(self, tag: str) -> List[Skill]:
        return [s for s in self._skills.values() if tag in s.tags]

    def get_favorite_skills(self) -> List[Skill]:
        return [s for s in self._skills.values() if s.favorite]

    def get_recent_skills(self, limit: int = 10) -> List[Skill]:
        sorted_skills = sorted(
            self._skills.values(), key=lambda x: x.created_at, reverse=True
        )
        return sorted_skills[:limit]

    def update_skill(self, skill_id: str, updates: Dict[str, Any]) -> bool:
        if skill_id not in self._skills:
            return False

        skill = self._skills[skill_id]

        for key, value in updates.items():
            if hasattr(skill, key):
                setattr(skill, key, value)

        self._save_library()
        return True

    def increment_use_count(self, skill_id: str):
        if skill_id in self._skills:
            skill = self._skills[skill_id]
            skill.use_count += 1
            skill.last_used = time.time()
            self._save_library()

    def toggle_favorite(self, skill_id: str) -> bool:
        if skill_id in self._skills:
            skill = self._skills[skill_id]
            skill.favorite = not skill.favorite
            self._save_library()
            return skill.favorite
        return False

    def delete_skill(self, skill_id: str) -> bool:
        if skill_id not in self._skills:
            return False

        skill = self._skills[skill_id]

        script_file = self._scripts_dir / f"{skill_id}.{skill.script_type}"
        if script_file.exists():
            script_file.unlink()

        del self._skills[skill_id]
        self._save_library()

        logger.info(f"Deleted skill: {skill_id}")
        return True

    def export_skill(self, skill_id: str, format: str = None) -> ExportResult:
        if skill_id not in self._skills:
            return ExportResult(False, "", "", "Skill not found")

        skill = self._skills[skill_id]
        export_format = format or skill.script_type

        timestamp = int(time.time())

        if export_format == "python":
            filename = f"{skill.name.replace(' ', '_')}_{timestamp}.py"
        elif export_format == "powershell":
            filename = f"{skill.name.replace(' ', '_')}_{timestamp}.ps1"
        elif export_format == "workflow":
            filename = f"{skill.name.replace(' ', '_')}_{timestamp}.json"
        elif export_format == "batch":
            filename = f"{skill.name.replace(' ', '_')}_{timestamp}.bat"
        else:
            filename = f"{skill.name.replace(' ', '_')}_{timestamp}.txt"

        output_path = self._exports_dir / filename

        content = skill.script_content

        if export_format == "workflow" and skill.script_type != "workflow":
            content = json.dumps(
                {
                    "name": skill.name,
                    "description": skill.description,
                    "skill_id": skill.skill_id,
                    "script_type": skill.script_type,
                    "script_content": skill.script_content,
                },
                indent=2,
            )

        elif export_format == "batch" and skill.script_type == "python":
            content = f'@echo off\npython "{skill.name.replace(" ", "_")}.py"\npause\n'

        output_path.write_text(content)
        skill.exported = True
        self._save_library()

        logger.info(f"Exported skill: {skill.name} -> {output_path}")
        return ExportResult(True, str(output_path), export_format)

    def export_all_skills(self, format: str = "python") -> List[ExportResult]:
        results = []

        for skill_id in self._skills:
            result = self.export_skill(skill_id, format)
            results.append(result)

        return results

    def import_skill(
        self, file_path: str, name: str = None, description: str = ""
    ) -> Optional[str]:
        file = Path(file_path)

        if not file.exists():
            logger.error(f"File not found: {file_path}")
            return None

        try:
            content = file.read_text()
            ext = file.suffix.lower()

            script_type_map = {
                ".py": "python",
                ".ps1": "powershell",
                ".bat": "batch",
                ".sh": "bash",
                ".json": "workflow",
            }

            script_type = script_type_map.get(ext, "text")

            skill_name = name or file.stem

            skill_id = hashlib.md5(f"{skill_name}{time.time()}".encode()).hexdigest()[
                :12
            ]

            skill = Skill(
                skill_id=skill_id,
                name=skill_name,
                description=description or f"Imported from {file.name}",
                pattern_id="",
                script_content=content,
                script_type=script_type,
            )

            return self.save_skill(skill)

        except Exception as e:
            logger.error(f"Failed to import skill: {e}")
            return None

    def sync_to_cloud(self) -> Tuple[bool, str]:
        if not self._cloud_dir:
            return False, "Cloud directory not configured"

        try:
            cloud_skills = self._cloud_path / "skills"
            cloud_skills.mkdir(exist_ok=True)

            for skill_id, skill in self._skills.items():
                cloud_file = cloud_skills / f"{skill_id}.json"
                cloud_file.write_text(json.dumps(skill.to_dict(), indent=2))
                skill.cloud_synced = True

            self._save_library()
            logger.info(f"Synced {len(self._skills)} skills to cloud")

            return True, f"Synced {len(self._skills)} skills"

        except Exception as e:
            logger.error(f"Cloud sync failed: {e}")
            return False, str(e)

    def load_from_cloud(self) -> int:
        if not self._cloud_dir:
            return 0

        cloud_skills = self._cloud_path / "skills"

        if not cloud_skills.exists():
            return 0

        loaded = 0

        for skill_file in cloud_skills.glob("*.json"):
            try:
                data = json.loads(skill_file.read_text())
                skill = Skill(**data)

                if skill.skill_id not in self._skills:
                    self._skills[skill.skill_id] = skill
                    loaded += 1

            except Exception as e:
                logger.error(f"Failed to load cloud skill: {e}")

        if loaded > 0:
            self._save_library()

        logger.info(f"Loaded {loaded} skills from cloud")
        return loaded

    def search_skills(self, query: str) -> List[Skill]:
        query_lower = query.lower()
        results = []

        for skill in self._skills.values():
            if query_lower in skill.name.lower():
                results.append(skill)
            elif query_lower in skill.description.lower():
                results.append(skill)
            elif any(query_lower in tag.lower() for tag in skill.tags):
                results.append(skill)

        return results

    def get_stats(self) -> Dict[str, Any]:
        total_skills = len(self._skills)
        total_uses = sum(s.use_count for s in self._skills.values())
        favorites = len([s for s in self._skills.values() if s.favorite])
        exported = len([s for s in self._skills.values() if s.exported])

        types: Dict[str, int] = {}
        for skill in self._skills.values():
            types[skill.script_type] = types.get(skill.script_type, 0) + 1

        return {
            "total_skills": total_skills,
            "total_uses": total_uses,
            "favorites": favorites,
            "exported": exported,
            "by_type": types,
            "cloud_enabled": self._cloud_dir is not None,
        }

    def get_status(self) -> dict:
        return {
            "skills_count": len(self._skills),
            "library_dir": str(self.library_dir),
            "scripts_dir": str(self._scripts_dir),
            "exports_dir": str(self._exports_dir),
            "cloud_configured": self._cloud_dir is not None,
        }
