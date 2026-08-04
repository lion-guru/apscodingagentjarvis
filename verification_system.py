"""
Verification System for Jarvis/DevMind
Inspired by JarvisCodex - validates code changes before completion
"""
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import shutil

VERIFICATION_LOG = Path(".devmind") / "verification_log.json"
VERIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)

class VerificationSystem:
    def __init__(self):
        self.checkpoints = {}
        self.verification_history = []
        self.load_history()

    def load_history(self):
        """Load verification history from file"""
        if VERIFICATION_LOG.exists():
            try:
                with open(VERIFICATION_LOG, 'r', encoding='utf-8') as f:
                    self.verification_history = json.load(f)
            except Exception:
                self.verification_history = []

    def save_history(self):
        """Save verification history to file"""
        with open(VERIFICATION_LOG, 'w', encoding='utf-8') as f:
            json.dump(self.verification_history, f, indent=2)

    def create_checkpoint(self, file_path: str) -> str:
        """Create a checkpoint before making changes"""
        try:
            p = Path(file_path)
            if not p.exists():
                return None  # No need to checkpoint new files
            
            # Create backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{p.name}_{timestamp}.bak"
            backup_path = p.parent / ".devmind" / "checkpoints" / backup_name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(p, backup_path)
            
            checkpoint_id = backup_name
            self.checkpoints[checkpoint_id] = {
                "original": str(p),
                "backup": str(backup_path),
                "timestamp": timestamp
            }
            
            return checkpoint_id
        except Exception as e:
            print(f"[VERIFICATION] Failed to create checkpoint: {e}")
            return None

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore from checkpoint"""
        try:
            if checkpoint_id not in self.checkpoints:
                print(f"[VERIFICATION] Checkpoint not found: {checkpoint_id}")
                return False
            
            checkpoint = self.checkpoints[checkpoint_id]
            original = Path(checkpoint["original"])
            backup = Path(checkpoint["backup"])
            
            if backup.exists():
                shutil.copy2(backup, original)
                print(f"[VERIFICATION] Restored from checkpoint: {checkpoint_id}")
                return True
            else:
                print(f"[VERIFICATION] Backup file not found: {backup}")
                return False
        except Exception as e:
            print(f"[VERIFICATION] Failed to restore checkpoint: {e}")
            return False

    def verify_syntax(self, file_path: str) -> Dict:
        """Verify file syntax"""
        result = {
            "file": file_path,
            "syntax_valid": True,
            "errors": []
        }
        
        try:
            p = Path(file_path)
            if not p.exists():
                result["syntax_valid"] = False
                result["errors"].append("File does not exist")
                return result
            
            # Check for common syntax errors based on extension
            ext = p.suffix.lower()
            
            if ext == '.py':
                # Python syntax check
                process = subprocess.run(
                    ['python', '-m', 'py_compile', str(p)],
                    capture_output=True,
                    text=True
                )
                if process.returncode != 0:
                    result["syntax_valid"] = False
                    result["errors"].append(process.stderr)
            
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                # JavaScript/TypeScript syntax check
                if ext in ['.ts', '.tsx']:
                    checker = 'tsc'
                else:
                    checker = 'node'
                    # Try eslint for JS
                    process = subprocess.run(
                        ['npx', '-y', 'eslint', str(p)],
                        capture_output=True,
                        text=True
                    )
                    if process.returncode != 0:
                        result["syntax_valid"] = False
                        result["errors"].append(process.stdout)
            
            elif ext == '.php':
                # PHP syntax check
                process = subprocess.run(
                    ['php', '-l', str(p)],
                    capture_output=True,
                    text=True
                )
                if process.returncode != 0:
                    result["syntax_valid"] = False
                    result["errors"].append(process.stderr)
            
        except Exception as e:
            result["syntax_valid"] = False
            result["errors"].append(f"Syntax check error: {e}")
        
        return result

    def verify_tests(self, project_path: str) -> Dict:
        """Run project tests and verify they pass"""
        result = {
            "project": project_path,
            "tests_run": False,
            "tests_passed": False,
            "failures": []
        }
        
        try:
            p = Path(project_path)
            if not p.exists():
                result["failures"].append("Project path does not exist")
                return result
            
            # Check for common test frameworks
            test_commands = []
            
            # Check for pytest
            if (p / "pytest.ini").exists() or (p / "tests").exists():
                test_commands.append(['python', '-m', 'pytest', '-v'])
            
            # Check for npm test
            if (p / "package.json").exists():
                test_commands.append(['npm', 'test'])
            
            # Check for PHP tests
            if (p / "phpunit.xml").exists() or (p / "tests").exists():
                test_commands.append(['php', 'vendor/bin/phpunit'])
            
            if not test_commands:
                result["failures"].append("No test framework detected")
                return result
            
            # Run first available test command
            for cmd in test_commands:
                try:
                    process = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        cwd=str(p),
                        timeout=60
                    )
                    result["tests_run"] = True
                    result["tests_passed"] = process.returncode == 0
                    
                    if not result["tests_passed"]:
                        result["failures"].append(process.stdout)
                        result["failures"].append(process.stderr)
                    
                    break  # Use first successful command
                except subprocess.TimeoutExpired:
                    result["failures"].append("Tests timed out")
                    break
                except Exception as e:
                    result["failures"].append(f"Test execution error: {e}")
                    continue
            
        except Exception as e:
            result["failures"].append(f"Test verification error: {e}")
        
        return result

    def verify_changes(self, file_path: str, project_path: str) -> Dict:
        """Complete verification of changes"""
        verification_result = {
            "file": file_path,
            "timestamp": datetime.now().isoformat(),
            "syntax": {},
            "tests": {},
            "overall_valid": True
        }
        
        # Create checkpoint
        checkpoint_id = self.create_checkpoint(file_path)
        verification_result["checkpoint_id"] = checkpoint_id
        
        # Verify syntax
        syntax_result = self.verify_syntax(file_path)
        verification_result["syntax"] = syntax_result
        
        if not syntax_result["syntax_valid"]:
            verification_result["overall_valid"] = False
        
        # Verify tests if project path provided
        if project_path:
            test_result = self.verify_tests(project_path)
            verification_result["tests"] = test_result
            
            if test_result.get("tests_run") and not test_result.get("tests_passed"):
                verification_result["overall_valid"] = False
        
        # Save to history
        self.verification_history.append(verification_result)
        self.save_history()
        
        return verification_result

    def get_verification_report(self, last_n: int = 10) -> List[Dict]:
        """Get last N verification results"""
        return self.verification_history[-last_n:]

# Global verification system instance
verification_system = VerificationSystem()

def verify_before_completion(file_path: str, project_path: str = None) -> bool:
    """Verify changes before marking task as complete"""
    result = verification_system.verify_changes(file_path, project_path)
    
    if result["overall_valid"]:
        print(f"[VERIFICATION] ✅ Changes verified successfully")
        return True
    else:
        print(f"[VERIFICATION] ❌ Verification failed")
        if result["syntax"]["errors"]:
            print(f"  Syntax errors: {result['syntax']['errors']}")
        if result["tests"]["failures"]:
            print(f"  Test failures: {result['tests']['failures']}")
        
        # Offer to restore checkpoint
        if result.get("checkpoint_id"):
            print(f"[VERIFICATION] Checkpoint available: {result['checkpoint_id']}")
            print(f"[VERIFICATION] Use restore_checkpoint() to revert changes")
        
        return False

def restore_last_checkpoint(checkpoint_id: str) -> bool:
    """Restore the last checkpoint"""
    return verification_system.restore_checkpoint(checkpoint_id)

if __name__ == "__main__":
    # Test verification system
    print("Testing Verification System")
    print("=" * 50)
    
    # Test syntax verification
    test_file = "agent.py"
    if Path(test_file).exists():
        result = verification_system.verify_syntax(test_file)
        print(f"Syntax verification for {test_file}:")
        print(f"  Valid: {result['syntax_valid']}")
        if result['errors']:
            print(f"  Errors: {result['errors']}")
    
    # Test complete verification
    if Path(test_file).exists():
        result = verification_system.verify_changes(test_file, ".")
        print(f"\nComplete verification for {test_file}:")
        print(f"  Overall Valid: {result['overall_valid']}")
        print(f"  Checkpoint ID: {result.get('checkpoint_id')}")
