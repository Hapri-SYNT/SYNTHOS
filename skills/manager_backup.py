# skills/manager.py — FINAL
import os
import logging
import importlib.util
from typing import Dict, Optional


class SkillManager:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self.skills_cache: Dict[str, Dict] = {}
        self._load_all_skills()

    def _load_all_skills(self):
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir, exist_ok=True)
            return

        for skill_folder in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_folder)
            if not os.path.isdir(skill_path) or skill_folder.startswith('__'):
                continue

            skill_data = {"name": skill_folder, "path": skill_path}

            # Load executor dari executor.py (WAJIB)
            executor_file = os.path.join(skill_path, "executor.py")
            if not os.path.exists(executor_file):
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    f"skills.{skill_folder}.executor", executor_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if isinstance(obj, type) and attr_name not in ("SkillManager",):
                        skill_data["executor"] = obj()
                        break
            except Exception as e:
                logging.warning(f"Gagal load executor dari {skill_folder}: {e}")
                continue

            self.skills_cache[skill_folder] = skill_data

        logging.info(f"📚 Skill Manager: {len(self.skills_cache)} skills loaded")

    def get_skill(self, skill_name: str) -> Optional[Dict]:
        return self.skills_cache.get(skill_name)

    def execute_skill(self, dna, skill_name: str, *args, **kwargs):
        skill = self.get_skill(skill_name)
        if not skill or "executor" not in skill:
            dna.log_action(f"❌ Skill {skill_name} tidak memiliki executor")
            return None
        try:
            executor = skill["executor"]
            if hasattr(executor, "execute"):
                return executor.execute(dna, *args, **kwargs)
            else:
                dna.log_action(f"❌ Executor {skill_name} tidak memiliki metode execute")
                return None
        except Exception as e:
            dna.log_action(f"❌ Error executing skill {skill_name}: {e}")
            return None


skill_manager = SkillManager()
