"""
DevMind Model Selector - Dynamically lists all installed Ollama models + Gemini options
"""
import subprocess
import sys
import os

GEMINI_MODELS = [
    ("gemini-2.0-flash",      "✨ Gemini 2.0 Flash  (Online, Free, Fastest)"),
    ("gemini-1.5-flash",      "🌟 Gemini 1.5 Flash  (Online, Free)"),
    ("gemini-1.5-pro",        "💎 Gemini 1.5 Pro    (Online, Free, Smartest)"),
]

OPENROUTER_MODELS = [
    ("google/gemma-2-9b-it:free",             "🧠 Gemma 2 9B IT (OpenRouter Free — Active)"),
    ("meta-llama/llama-3.2-1b-instruct:free", "🦙 Llama 3.2 1B (OpenRouter Free — Fast)"),
    ("deepseek/deepseek-r1:free",             "🤖 DeepSeek R1 (OpenRouter Free)"),
    ("mistralai/mistral-7b-instruct:free",    "🌪️ Mistral 7B (OpenRouter Free)"),
    ("qwen/qwen-2.5-coder-32b-instruct",      "💻 Qwen 2.5 Coder 32B (OpenRouter Standard)"),
]



def get_ollama_models():
    """Get all locally installed Ollama models"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().splitlines()
        models = []
        for line in lines[1:]:  # skip header
            parts = line.split()
            if parts:
                name = parts[0]
                if ":" not in name:
                    name += ":latest"
                models.append(name)
        return models
    except Exception:
        return []

def main():
    print()
    print("=" * 50)
    print("  DevMind — Select AI Model")
    print("=" * 50)

    ollama_models = get_ollama_models()
    all_options = []

    # Local Ollama models
    if ollama_models:
        print("\n  📦 LOCAL MODELS (Offline, Private):")
        for m in ollama_models:
            idx = len(all_options) + 1
            label = f"⚡ {m}"
            print(f"    [{idx}] {label}")
            all_options.append(m)
    else:
        print("\n  ⚠️  No local Ollama models found.")
        print("      Install one with: ollama pull qwen2.5-coder:7b")

    # Gemini online models
    print("\n  🌐 ONLINE MODELS (Gemini API — Free Tier):")
    for value, label in GEMINI_MODELS:
        idx = len(all_options) + 1
        print(f"    [{idx}] {label}")
        all_options.append(value)

    # OpenRouter free models
    print("\n  🌐 ONLINE MODELS (OpenRouter — Free Tier):")
    for value, label in OPENROUTER_MODELS:
        idx = len(all_options) + 1
        print(f"    [{idx}] {label}")
        all_options.append(value)

    print()
    print("=" * 50)

    default_idx = 1
    # Prefer 7b if installed
    for i, m in enumerate(all_options):
        if "7b" in m.lower():
            default_idx = i + 1
            break

    try:
        choice = input(f"  Enter choice [1-{len(all_options)}, default {default_idx}]: ").strip()
        if not choice:
            choice = str(default_idx)
        idx = int(choice) - 1
        if 0 <= idx < len(all_options):
            selected = all_options[idx]
        else:
            print("  Invalid choice, using default.")
            selected = all_options[default_idx - 1]
    except (ValueError, KeyboardInterrupt):
        selected = all_options[default_idx - 1] if all_options else "gemini-2.0-flash"

    # Write selection to temp file for bat to read
    with open("_selected_model.tmp", "w") as f:
        f.write(selected)

    print(f"\n  ✅ Selected: {selected}")
    print("=" * 50)
    print()

if __name__ == "__main__":
    main()
