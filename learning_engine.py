import os
import json
import re
from pathlib import Path

STYLE_FILE = "style_guide.json"

def scan_codebase_for_styles(cwd: str) -> dict:
    """Scans code files (PHP, JS, CSS, Python) to detect coding styles and patterns."""
    styles = {
        "php": {
            "database_api": "unknown",
            "framework": "vanilla",
            "helper_functions": [],
            "patterns": []
        },
        "javascript": {
            "module_system": "unknown",
            "framework": "vanilla",
            "formatting": "unknown"
        },
        "css": {
            "preprocessor": "vanilla",
            "naming_style": "vanilla"
        },
        "general": {
            "indentation": "spaces",
            "custom_rules": []
        }
    }

    # Load existing to preserve custom rules
    existing = load_style_guide(cwd)
    if existing:
        styles["general"]["custom_rules"] = existing.get("general", {}).get("custom_rules", [])
        styles["php"]["helper_functions"] = existing.get("php", {}).get("helper_functions", [])

    extensions = {'.php', '.js', '.css', '.py'}
    scanned_count = 0

    # Quick scans
    for root, dirs, files in os.walk(cwd):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '__pycache__', 'venv', '.venv', 'env', '.agents')]
        for f in files:
            path = Path(root) / f
            if path.suffix not in extensions:
                continue

            scanned_count += 1
            if scanned_count > 100: # Limit scans to prevent hanging
                break

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                
                # Check Indentation
                if "\t" in content[:2000]:
                    styles["general"]["indentation"] = "tabs"

                # PHP Analysis
                if path.suffix == '.php':
                    if "mysqli_connect" in content or "new mysqli" in content:
                        styles["php"]["database_api"] = "mysqli"
                    elif "PDO(" in content:
                        styles["php"]["database_api"] = "PDO"
                    
                    if "Laravel" in content or "Illuminate\\" in content:
                        styles["php"]["framework"] = "Laravel"
                    elif "CodeIgniter" in content:
                        styles["php"]["framework"] = "CodeIgniter"
                        
                    # Find custom connect functions
                    db_connect_funcs = re.findall(r'function\s+([a-zA-Z0-9_]*connect[a-zA-Z0-9_]*)', content, re.IGNORECASE)
                    for func in db_connect_funcs:
                        if func not in styles["php"]["helper_functions"]:
                            styles["php"]["helper_functions"].append(func)

                # JS Analysis
                elif path.suffix == '.js':
                    if "require(" in content:
                        styles["javascript"]["module_system"] = "CommonJS (require)"
                    elif "import " in content and " from " in content:
                        styles["javascript"]["module_system"] = "ES6 Modules (import)"
                        
                    if "React" in content or "useState(" in content:
                        styles["javascript"]["framework"] = "React"
                    elif "Vue" in content:
                        styles["javascript"]["framework"] = "Vue"
                    elif "$" in content or "jQuery" in content:
                        styles["javascript"]["framework"] = "jQuery"

                # CSS Analysis
                elif path.suffix == '.css':
                    if "@import" in content:
                        styles["css"]["naming_style"] = "Modular"
                    if "bootstrap" in content.lower():
                        styles["css"]["naming_style"] = "Bootstrap Utility"

            except Exception:
                pass

    save_style_guide(cwd, styles)
    return styles

def load_style_guide(cwd: str) -> dict:
    path = Path(cwd) / STYLE_FILE
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_style_guide(cwd: str, styles: dict):
    path = Path(cwd) / STYLE_FILE
    path.write_text(json.dumps(styles, indent=2), encoding="utf-8")

def learn_new_rule(cwd: str, category: str, rule: str) -> str:
    """Adds a newly learned pattern/rule to the style guide database."""
    styles = load_style_guide(cwd)
    if not styles:
        styles = scan_codebase_for_styles(cwd)
        
    if "general" not in styles:
        styles["general"] = {}
    if "custom_rules" not in styles["general"]:
        styles["general"]["custom_rules"] = []
        
    rule_entry = {"category": category, "rule": rule}
    if rule_entry not in styles["general"]["custom_rules"]:
        styles["general"]["custom_rules"].append(rule_entry)
        save_style_guide(cwd, styles)
        return f"Successfully learned new pattern: [{category}] {rule}"
    return "Pattern already exists in style guide."

def generate_style_prompt_extension(cwd: str) -> str:
    """Generates a text block describing code conventions to inject into the system prompt."""
    styles = load_style_guide(cwd)
    if not styles:
        # Scan if file doesn't exist
        styles = scan_codebase_for_styles(cwd)
        
    prompt_lines = []
    prompt_lines.append("\n## 📝 Learned Coding Conventions & Styles (User Preferences)")
    
    prompt_lines.append(f"- Indentation preference: Use {styles.get('general', {}).get('indentation', 'spaces')}.")
    
    # PHP preferences
    php = styles.get("php", {})
    if php.get("database_api") != "unknown":
        prompt_lines.append(f"- PHP Database API: Prefer using {php.get('database_api')}.")
    if php.get("helper_functions"):
        prompt_lines.append(f"- PHP DB Helpers detected: {', '.join(php.get('helper_functions'))}. Look for these helper functions when connecting to MySQL.")
    if php.get("framework") != "vanilla":
        prompt_lines.append(f"- PHP Framework: Project uses {php.get('framework')}.")
        
    # JS preferences
    js = styles.get("javascript", {})
    if js.get("module_system") != "unknown":
        prompt_lines.append(f"- JS Import Style: Use {js.get('module_system')}.")
    if js.get("framework") != "vanilla":
        prompt_lines.append(f"- JS Framework: Project uses {js.get('framework')}.")
        
    # Custom learned rules
    custom_rules = styles.get("general", {}).get("custom_rules", [])
    if custom_rules:
        prompt_lines.append("- Custom Project Rules:")
        for r in custom_rules:
            prompt_lines.append(f"  * [{r['category']}] {r['rule']}")
            
    return "\n".join(prompt_lines)
