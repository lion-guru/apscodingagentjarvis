import os
import sys
import json
import subprocess
from pathlib import Path

CONFIG_FILE = "llama_factory_config.yaml"
DATASET_FILE = "refine_dataset.json"
OUTPUT_DIR = "devmind_tuned_model"

def check_env_and_gpu():
    """Verify system capabilities for local training."""
    print("🖥️ Checking system configurations...")
    
    # 1. Check for PyTorch & CUDA
    has_cuda = False
    try:
        import torch
        print(f"  PyTorch Version: {torch.__version__}")
        if torch.cuda.is_available():
            has_cuda = True
            device_name = torch.cuda.get_device_name(0)
            print(f"  CUDA GPU Detected: ✅ {device_name}")
            print(f"  VRAM Available: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
        else:
            print("  CUDA GPU: ❌ Not detected (Falling back to CPU mode).")
    except ImportError:
        print("  PyTorch: ❌ Not installed. Run 'pip install torch' to check GPU capabilities.")

    # 2. Check if distilled dataset exists, fallback to raw
    active_dataset = "refined_distilled_dataset.json" if Path("refined_distilled_dataset.json").exists() else DATASET_FILE
    if not Path(active_dataset).exists():
        print(f"  Dataset ({active_dataset}): ❌ Not found. Running compiler first...")
        try:
            import refine_model
            refine_model.compile_fine_tuning_dataset()
        except ImportError:
            print("  Dataset Compiler: Failed to import refine_model.py.")
    else:
        print(f"  Dataset ({active_dataset}): ✅ Ready (Google Distillation: {'Yes' if 'distilled' in active_dataset else 'No'}).")

    return has_cuda

def generate_llama_factory_config(has_cuda: bool):
    """Write the training config YAML for LLaMA-Factory."""
    # Support Qwen 2.5 Coder & Google Gemma 2
    # Gemma 2 2B/9B is Google's new state-of-the-art model designed to run extremely fast on local PCs
    prefer_gemma = True # Set to true to utilize Google's advanced Gemma 2 tech
    
    if prefer_gemma:
        base_model = "google/gemma-2-2b-it" if not has_cuda else "google/gemma-2-9b-it"
        template = "gemma"
    else:
        base_model = "Qwen/Qwen2.5-Coder-3B-Instruct" if not has_cuda else "Qwen/Qwen2.5-Coder-7B-Instruct"
        template = "qwen"
        
    active_dataset_file = "refined_distilled_dataset.json" if Path("refined_distilled_dataset.json").exists() else DATASET_FILE
    
    config_data = f"""# LLaMA-Factory Fine-Tuning Configuration
model_name_or_path: {base_model}
stage: sft
do_train: true
finetuning_type: lora
lora_target: all

# Dataset
dataset: devmind_dataset
dataset_dir: .
template: {template}
cutoff_len: 1024
max_samples: 1000
overwrite_cache: true
preprocessing_num_workers: 4

# Output
output_dir: {OUTPUT_DIR}
logging_steps: 10
save_steps: 100
plot_loss: true
overwrite_output_dir: true

# Hyperparameters
per_device_train_batch_size: 2
gradient_accumulation_steps: 4
learning_rate: 1.0e-4
num_train_epochs: 3.0
lr_scheduler_type: cosine
warmup_ratio: 0.1
fp16: {str(has_cuda).lower()}

# Export / Device settings
device: {"cuda" if has_cuda else "cpu"}
"""
    # Write dataset info to dataset_info.json for LLaMA-Factory registration
    dataset_info = {
        "devmind_dataset": {
            "file_name": active_dataset_file,
            "columns": {
                "prompt": "instruction",
                "query": "input",
                "response": "output"
            }
        }
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write(config_data)
    with open("dataset_info.json", 'w', encoding='utf-8') as f:
        json.dump(dataset_info, f, indent=2)
        
    print(f"📝 Configuration written to '{CONFIG_FILE}'.")

def start_training():
    has_cuda = check_env_and_gpu()
    generate_llama_factory_config(has_cuda)
    
    # Check if dataset is empty
    try:
        with open(DATASET_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if len(data) < 5:
                print("\n⚠️ WARNING: Your dataset has very few examples. It is highly recommended to have at least 50+ examples before starting fine-tuning.")
                print("Keep using the agentic coder to log more successful sessions!")
    except Exception:
        pass

    print("\n=== STARTING FINE-TUNING ===")
    print("To trigger the training pipeline, run this command in your terminal:")
    print("  llamafactory-cli train llama_factory_config.yaml")
    print("\nThis will perform a LoRA (Low-Rank Adaptation) fine-tuning of Qwen 2.5 Coder on your style logs.")
    
    print("\n=== CONVERTING TO OLLAMA (GGUF) ===")
    print("Once training completes, convert your model to GGUF format for Ollama:")
    print(f"1. Merge LoRA weights:")
    print(f"   llamafactory-cli export merge_config.yaml  (We will auto-generate merge settings)")
    print("2. Convert to GGUF using llama.cpp:")
    print("   python llama.cpp/convert_hf_to_gguf.py devmind_merged_model --outtype q4_k_m")
    print("3. Add to Ollama:")
    print("   Create a 'Modelfile' containing: FROM devmind_merged_model-q4_k_m.gguf")
    print("   Run: 'ollama create my_coder_model -f Modelfile'")
    
    # Auto-generate merge config
    base_model = "Qwen/Qwen2.5-Coder-3B-Instruct" if not has_cuda else "Qwen/Qwen2.5-Coder-7B-Instruct"
    merge_config = {
        "model_name_or_path": base_model,
        "adapter_name_or_path": OUTPUT_DIR,
        "template": "qwen",
        "finetuning_type": "lora",
        "export_dir": "devmind_merged_model",
        "export_size": 2,
        "export_device": "cpu",
        "export_legacy_format": False
    }
    with open("merge_config.yaml", 'w', encoding='utf-8') as f:
        # Simple yaml writer
        for k, v in merge_config.items():
            f.write(f"{k}: {v}\n")

if __name__ == "__main__":
    start_training()
