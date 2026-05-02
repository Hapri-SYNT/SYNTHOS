import sys
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
                # Register module di sys.modules biar dataclass ga error
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                # Cari class yang punya method 'execute' (bukan class pertama)
                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if isinstance(obj, type) and attr_name not in ("SkillManager",):
                        # Skip class dari library eksternal
                        obj_module = getattr(obj, '__module__', '')
                        if 'concurrent' in obj_module or 'asyncio' in obj_module or 'abc' in obj_module or attr_name.startswith('_'):
                            continue
                        # Prioritaskan class dengan 'execute' method atau nama spesifik
                        if attr_name.startswith('_') or attr_name in ('ABC', 'abstractmethod'):
                            continue
                        if hasattr(obj, 'execute') and (attr_name.startswith('UHEE') or attr_name.endswith('Executor') or attr_name.endswith('Bridge') or attr_name.endswith('Agent') or attr_name == 'CodeGenerator'):
                            skill_data["executor"] = obj()
                            break
                # Fallback: class pertama yang bisa di-instantiate
                if "executor" not in skill_data:
                    for attr_name in dir(module):
                        obj = getattr(module, attr_name)
                        if isinstance(obj, type) and attr_name not in ("SkillManager",):
                            try:
                                skill_data["executor"] = obj()
                                break
                            except:
                                continue
            except Exception as e:
                logging.warning(f"Gagal load executor dari {skill_folder}: {e}")
                continue

            self.skills_cache[skill_folder] = skill_data

        logging.info(f"📚 Skill Manager: {len(self.skills_cache)} skills loaded")

    def get_skill(self, skill_name: str) -> Optional[Dict]:
        return self.skills_cache.get(skill_name)

    def _ensure_syntosh(self, dna):
        """Pastikan DNA punya akses SYNTOSH. Inject kalau belum ada."""
        if not hasattr(dna, 'syntosh_reason') or dna.syntosh_reason is None:
            try:
                from SYNTOSH.syntosh_gpt_bridge import reason as syntosh_reason
                dna.syntosh_reason = syntosh_reason
                dna.state["syntosh_connected"] = True
            except Exception:
                pass

    def execute_skill(self, dna, skill_name: str, *args, **kwargs):
        skill = self.get_skill(skill_name)
        if not skill or "executor" not in skill:
            dna.log_action(f"❌ Skill {skill_name} tidak memiliki executor")
            return None
        try:
            self._ensure_syntosh(dna)
            executor = skill["executor"]
            if hasattr(executor, "execute"):
                import inspect
                sig = inspect.signature(executor.execute)
                params = list(sig.parameters.keys())
                # Filter kwargs yang ga ada di signature
                filtered_kwargs = {k: v for k, v in kwargs.items() if k in params}
                # Kalau cuma terima dna, jangan kirim kwargs
                if len(params) <= 2 and 'task' not in params:
                    return executor.execute(dna)
                elif 'task' in params:
                    return executor.execute(dna, task=kwargs.get('task', kwargs.get('query', '')))
                else:
                    return executor.execute(dna, **filtered_kwargs)
            else:
                dna.log_action(f"❌ Executor {skill_name} tidak memiliki metode execute")
                return None
        except Exception as e:
            dna.log_action(f"❌ Error executing skill {skill_name}: {e}")
            return None


skill_manager = SkillManager()
