class TrinitasBridge:
    def execute(self, dna, task: str = None):
        if task is None:
            task = "general_task"
        # Default: gunakan claw_action, nanti bisa disesuaikan
        result = self.claw_action(dna, task)
        return result

    def claw_action(self, dna, task: str):
        result = {"task": task, "status": "completed", "output": f"Claw executed: {task[:50]}"}
        dna.log_action(f"🦞 Claw: {task[:30]}...")
        return result

    def manus_action(self, dna, task: str):
        result = {"task": task, "status": "completed", "output": f"Manus executed: {task[:50]}"}
        dna.log_action(f"🤖 Manus: {task[:30]}...")
        return result
