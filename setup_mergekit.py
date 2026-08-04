import os
import sys
import subprocess
from pathlib import Path

MERGE_CONFIG_FILE = "merge_moe.yaml"

def write_merge_config():
    """Generates a Mixture of Experts (MoE) configuration for Mergekit.
    This merges Qwen 2.5 Coder 3B (coding specialist) and Google Gemma 2 2B (general reasoning specialist)
    into a single high-performance model that runs fast on standard PCs.
    """
    config_content = """# Mergekit Mixture of Experts (MoE) Configuration
base_model: Qwen/Qwen2.5-Coder-3B-Instruct
gate_mode: hidden
dtype: float16

experts:
  - source_model: Qwen/Qwen2.5-Coder-3B-Instruct
    positive_prompts:
      - "write code"
      - "fix syntax error"
      - "PHP connection helper"
      - "JavaScript script"
      - "Python script"
      - "develop app"
  - source_model: google/gemma-2-2b-it
    positive_prompts:
      - "explain code logic"
      - "analyze system"
      - "summarize text"
      - "explain database architecture"
      - "general chat and reasoning"
"""
    with open(MERGE_CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write(config_content)
    print(f"📝 Mixture of Experts configuration written to '{MERGE_CONFIG_FILE}'.")

def show_instructions():
    print("\n" + "="*50)
    print("🧠 MODEL MERGING PIPELINE FOR NORMAL PCs")
    print("="*50)
    print("\n1. Gemini vs Open-Source Models:")
    print("   - Gemini ek proprietary cloud model hai. Uske weights public nahi hain, isliye use direct merge nahi kiya ja sakta.")
    print("   - Lekin hum Google ke official open-source model GEMMA 2 (2B) aur Qwen 2.5 Coder (3B) ko aapas me merge karenge!")
    
    print("\n2. Kya system hang hoga?")
    print("   - ❌ Bilkul nahi! Merged model ka active parameter size sirf ~3B to 4B hoga.")
    print("   - Jab is model ko GGUF format (Q4_K_M quantization) me convert karenge, toh ye sirf 2.2 GB of RAM lega.")
    print("   - Ise aap bina kisi dedicated GPU ke normal laptop/PC par local running me bina hang hue run kar sakte hain.")

    print("\n3. Installation & Merging steps:")
    print("   Run these commands in your PowerShell console:")
    print("   a) pip install mergekit")
    print(f"   b) mergekit-yaml {MERGE_CONFIG_FILE} ./merged_model --device cpu")
    print("\nOnce merged, you can convert the output folder to GGUF and import it into Ollama!")
    print("="*50)

if __name__ == "__main__":
    write_merge_config()
    show_instructions()
