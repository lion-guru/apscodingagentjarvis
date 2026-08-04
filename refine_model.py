import os
import json
import glob
from pathlib import Path

# Path to the ide logs
APP_DATA_DIR = Path("C:/Users/abhay/.gemini/antigravity-ide")
BRAIN_DIR = APP_DATA_DIR / "brain"
OUTPUT_DATASET = "refine_dataset.json"

def compile_fine_tuning_dataset():
    print("🚀 Starting Dataset Compiler for local Ollama fine-tuning...")
    dataset = []
    
    # Locate all transcript.jsonl files
    transcript_files = glob.glob(str(BRAIN_DIR / "**" / ".system_generated" / "logs" / "transcript.jsonl"), recursive=True)
    print(f"🔍 Found {len(transcript_files)} conversation logs.")
    
    for tf in transcript_files:
        try:
            with open(tf, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            current_instruction = None
            
            for line in lines:
                if not line.strip():
                    continue
                step = json.loads(line)
                
                # Check for User Input
                if step.get("type") == "USER_INPUT":
                    current_instruction = step.get("content", "")
                
                # Check for Assistant Response (Tool Call or final text)
                elif step.get("type") == "PLANNER_RESPONSE" and current_instruction:
                    content = step.get("content", "")
                    # We only want to train on successful actions
                    if content and step.get("status") == "DONE":
                        dataset.append({
                            "instruction": f"You are a local developer agent. Solve this task:\n{current_instruction}",
                            "input": "",
                            "output": content
                        })
                        # Reset to avoid duplicating same response
                        current_instruction = None
        except Exception as e:
            print(f"Error parsing log {tf}: {e}")
            
    # Save the dataset
    if dataset:
        with open(OUTPUT_DATASET, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"✅ Dataset compiled successfully! Saved {len(dataset)} examples to '{OUTPUT_DATASET}'.")
        print("\n=== HOW TO FINE-TUNE YOUR LOCAL MODEL ===")
        print("1. Install LLaMA-Factory: 'pip install llamafactory'")
        print(f"2. Use '{OUTPUT_DATASET}' as your custom training dataset.")
        print("3. Run fine-tuning on a base model like Qwen2.5-Coder-7B-Instruct:")
        print("   llamafactory-cli train config.yaml")
        print("Your model will learn your exact coding styles, tool signatures, and system behaviors!")
    else:
        print("⚠️ No successful session sequences found yet to compile. Keep coding with DevMind to build up logs!")

if __name__ == "__main__":
    compile_fine_tuning_dataset()
