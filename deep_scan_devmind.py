import os
import re
import json

base_dirs = [
    r"c:\Users\abhay\AppData\Local\Programs\stonic_dsktp",
    r"c:\Users\abhay\AppData\Roaming\stonic_dsktp",
    r"c:\Users\abhay\AppData\Local\stonic_dsktp"
]

out_report = r"E:\coding-assistant\devmind_deep_scan_report.txt"

patterns = {
    "Supabase / API Keys": r"(?:sk-[a-zA-Z0-9_\-]{20,}|AIzaSy[a-zA-Z0-9_\-]{33}|eyJ[a-zA-Z0-9_\-]{30,}\.[a-zA-Z0-9_\-]{30,})",
    "Bearer Tokens / Secret Keys": r"(?:secret|api_key|token|auth_key|private_key)[\"':\s=]+([a-zA-Z0-9_\-]{16,})",
    "Cloud & Backend Endpoints": r"https?://[a-zA-Z0-9_\-\.]+\.(?:supabase\.co|netlify\.app|onrender\.com|railway\.app|groq\.com|openrouter\.ai|stonic\.ai)",
    "Port & Gateway Endpoints": r"http://(?:127\.0\.0\.1|localhost):[0-9]{4,5}",
    "System Prompts / Agent Persona": r"(?:You are a|System Prompt|Persona|Instructions|You are an AI|Role:)[\s\S]{20,200}"
}

findings = {k: [] for k in patterns}
scanned_files = 0
found_config_files = []

for b_dir in base_dirs:
    if not os.path.exists(b_dir):
        continue
    for root, dirs, files in os.walk(b_dir):
        if "python" in root or "venv" in root or "Code Cache" in root or "GPUCache" in root:
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in [".json", ".env", ".yaml", ".yml", ".py", ".js", ".html", ".txt", ".md", ".config"]:
                f_path = os.path.join(root, f)
                found_config_files.append(f_path)
                scanned_files += 1
                try:
                    with open(f_path, "r", encoding="utf-8", errors="ignore") as file_obj:
                        content = file_obj.read()
                        for cat, pat in patterns.items():
                            matches = re.findall(pat, content)
                            for m in matches[:5]:
                                findings[cat].append((f_path, m[:100]))
                except Exception:
                    pass

report_lines = []
report_lines.append("========================================================")
report_lines.append("  DEVMIND AI STUDIO FORENSIC AUDIT REPORT")
report_lines.append("========================================================\n")
report_lines.append(f"Total Config/Script Files Scanned: {scanned_files}\n")

for cat, items in findings.items():
    report_lines.append(f"=== Category: {cat} ({len(items)} items found) ===")
    unique_items = list(dict.fromkeys(items))[:15]
    for path, match in unique_items:
        report_lines.append(f"  File: {path}")
        report_lines.append(f"  Match: {match}\n")

with open(out_report, "w", encoding="utf-8") as out_f:
    out_f.write("\n".join(report_lines))

print(f"Deep scan complete! Report written to {out_report}")
