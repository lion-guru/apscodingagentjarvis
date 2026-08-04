"""
Self-Evolving Skill Synthesis for Jarvis/DevMind
Inspired by rishaadj/JARVIS - Generates new Python skills automatically
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import time

SKILLS_DIR = Path.home() / ".devmind" / "skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

SKILL_TEMPLATE = '''# {skill_name}
# Auto-generated skill
# Generated: {timestamp}

import os
import subprocess
from pathlib import Path

def execute(**kwargs):
    """
    {description}
    
    Parameters:
    {params}
    """
    try:
        # Implementation
        result = None
        
        # Your code here
        
        return {{
            "success": True,
            "output": str(result) if result else "Skill executed successfully"
        }}
    except Exception as e:
        return {{
            "success": False,
            "error": str(e)
        }}

if __name__ == "__main__":
    # Test the skill
    result = execute()
    print(result)
'''

class SkillSynthesizer:
    def __init__(self):
        self.synthesis_history = []
        self.load_history()

    def load_history(self):
        """Load synthesis history"""
        history_file = SKILLS_DIR / "synthesis_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.synthesis_history = json.load(f)
            except Exception:
                self.synthesis_history = []

    def save_history(self):
        """Save synthesis history"""
        history_file = SKILLS_DIR / "synthesis_history.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(self.synthesis_history, f, indent=2)

    def synthesize_skill(self, task_description: str, context: str = "") -> Dict:
        """
        Synthesize a new skill for a given task
        This is a simplified version - in production, would use AI to generate code
        """
        # Generate skill name from task
        skill_name = task_description.lower().replace(" ", "_").replace("-", "_")[:50]
        skill_name = "".join(c for c in skill_name if c.isalnum() or c == "_")
        
        # Create skill file
        skill_file = SKILLS_DIR / f"{skill_name}.py"
        
        # Generate skill content
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        params = self.extract_params(task_description)
        
        skill_content = SKILL_TEMPLATE.format(
            skill_name=skill_name,
            timestamp=timestamp,
            description=task_description,
            params=self.format_params(params)
        )
        
        # Write skill file
        skill_file.write_text(skill_content, encoding='utf-8')
        
        # Test the skill
        test_result = self.test_skill(skill_file)
        
        # Record synthesis
        synthesis_record = {
            "skill_name": skill_name,
            "task": task_description,
            "context": context,
            "file": str(skill_file),
            "timestamp": timestamp,
            "test_result": test_result,
            "status": "success" if test_result.get("success") else "failed"
        }
        
        self.synthesis_history.append(synthesis_record)
        self.save_history()
        
        return synthesis_record

    def extract_params(self, task: str) -> List[str]:
        """Extract potential parameters from task description"""
        # Simple heuristic - extract words that look like parameters
        common_params = ["file", "path", "url", "name", "id", "directory", "folder"]
        params = []
        
        for param in common_params:
            if param in task.lower():
                params.append(param)
        
        return params

    def format_params(self, params: List[str]) -> str:
        """Format parameters for documentation"""
        if not params:
            return "    None"
        
        formatted = []
        for param in params:
            formatted.append(f"    {param}: parameter description")
        
        return "\n".join(formatted)

    def test_skill(self, skill_file: Path) -> Dict:
        """Test a newly synthesized skill"""
        try:
            # Try to import and execute
            import importlib.util
            spec = importlib.util.spec_from_file_location("skill", skill_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Try to execute
                if hasattr(module, 'execute'):
                    result = module.execute()
                    return result
                else:
                    return {"success": False, "error": "No execute function found"}
            else:
                return {"success": False, "error": "Could not load module"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_synthesis_report(self) -> List[Dict]:
        """Get report of all synthesized skills"""
        return self.synthesis_history

    def get_active_skills(self) -> List[str]:
        """Get list of all active skills"""
        skills = []
        for skill_file in SKILLS_DIR.glob("*.py"):
            if skill_file.name != "__init__.py" and skill_file.name != "synthesis_history.json":
                skills.append(skill_file.stem)
        return skills

# Global skill synthesizer instance
skill_synthesizer = SkillSynthesizer()

def synthesize_new_skill(task: str, context: str = "") -> Dict:
    """Public interface to synthesize a new skill"""
    return skill_synthesizer.synthesize_skill(task, context)

def get_synthesis_report() -> List[Dict]:
    """Get synthesis report"""
    return skill_synthesizer.get_synthesis_report()

def get_active_skills() -> List[str]:
    """Get active skills"""
    return skill_synthesizer.get_active_skills()

if __name__ == "__main__":
    # Test skill synthesis
    print("Testing Skill Synthesis")
    print("=" * 50)
    
    # Synthesize a skill
    result = synthesize_new_skill(
        task="Open a file and read its contents",
        context="General file operations"
    )
    
    print(f"Synthesis Result:")
    print(f"  Skill Name: {result['skill_name']}")
    print(f"  Status: {result['status']}")
    print(f"  File: {result['file']}")
    print(f"  Test Result: {result['test_result']}")
    
    # Get active skills
    skills = get_active_skills()
    print(f"\nActive Skills: {len(skills)}")
    for skill in skills[:5]:
        print(f"  - {skill}")
