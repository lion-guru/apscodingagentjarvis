"""
DevMind CLI — Terminal Interface
Inspired by Claude Code's main.tsx terminal experience
"""
import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

from agent import (
    build_system_prompt, create_tool_registry, execute_tool,
    extract_tool_calls, remove_tool_calls,
    ollama_chat, check_ollama,
    DEFAULT_MODEL, OLLAMA_BASE, MEMORY_FILE, SKILLS_DIR,
    load_memory, save_memory, load_skills,
    restore_last_turn, compact_history, translate_to_english
)

console = Console()

HISTORY_FILE  = Path.home() / ".devmind" / "history"
CHAT_LOGS_DIR = Path.home() / ".devmind" / "chats"
CHAT_LOGS_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


BANNER = """[bold cyan]
  ██████╗ ███████╗██╗   ██╗███╗   ███╗██╗███╗   ██╗██████╗ 
  ██╔══██╗██╔════╝██║   ██║████╗ ████║██║████╗  ██║██╔══██╗
  ██║  ██║█████╗  ██║   ██║██╔████╔██║██║██╔██╗ ██║██║  ██║
  ██║  ██║██╔══╝  ╚██╗ ██╔╝██║╚██╔╝██║██║██║╚██╗██║██║  ██║
  ██████╔╝███████╗ ╚████╔╝ ██║ ╚═╝ ██║██║██║ ╚████║██████╔╝
  ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ 
[/bold cyan][dim]  Local AI Coding Assistant — 100% Private, 100% Free[/dim]
"""


def confirm_callback(command: str, reason: str) -> bool:
    """Ask user to confirm sensitive commands"""
    console.print(Panel(
        f"[yellow]⚠️  Sensitive command detected:[/]\n\n"
        f"[bold]{command}[/]\n\n"
        f"Reason: {reason}",
        title="⚠️ Confirmation Required",
        border_style="yellow"
    ))
    try:
        answer = console.input("[yellow]Allow? (y/N): [/]").strip().lower()
        return answer in ('y', 'yes')
    except KeyboardInterrupt:
        return False


def run_agent_loop(user_input: str, messages: list, tools: dict, model: str, max_steps: int = 10) -> None:
    """
    Core agent loop — inspired by Claude Code's QueryEngine.ts agentic loop.
    Runs until no more tool calls or max_steps reached.
    """
    translated = translate_to_english(user_input)
    if translated != user_input:
        console.print(f"[dim]🌐 Auto-Translated: {translated}[/]")
        user_input = translated
        
    messages.append({"role": "user", "content": user_input})
    
    # Auto-compact history if context token usage is too high (inspired by autoCompact.ts)
    messages[:] = compact_history(messages, model)
    
    for step in range(max_steps):
        # Call Ollama
        with console.status(f"[cyan]🤔 Thinking...[/] [dim](step {step+1}/{max_steps})[/]", spinner="dots"):
            try:
                response = ollama_chat(messages, model=model)
            except httpx_error() as e:
                console.print(f"[red]❌ Ollama error: {e}[/]")
                return
        
        messages.append({"role": "assistant", "content": response})
        
        # Parse response
        tool_calls = extract_tool_calls(response)
        clean_text = remove_tool_calls(response)
        
        # Show clean text
        if clean_text.strip():
            console.print()
            console.print(Markdown(clean_text))
        
        # If no tool calls — we're done
        if not tool_calls:
            break
        
        # Execute tools
        tool_results = []
        for tc in tool_calls:
            tool_name = tc["tool"]
            params = tc.get("params", {})
            
            # Show what tool is being used
            param_preview = ""
            if params:
                first_val = list(params.values())[0]
                if isinstance(first_val, str):
                    param_preview = f" [dim]({first_val[:60]}{'...' if len(str(first_val)) > 60 else ''})[/]"
            
            console.print(f"\n[yellow]⚙[/] [bold]{tool_name}[/]{param_preview}")
            
            # Execute
            with console.status(f"[dim]Running {tool_name}...[/]", spinner="dots2"):
                result = execute_tool(tools, tool_name, params)
            
            # Display result
            if result.success:
                # Show truncated output
                display = result.output
                if len(display) > 1000:
                    display = display[:1000] + f"\n[dim]... (truncated, {len(result.output)} total chars)[/]"
                console.print(Panel(
                    display, 
                    title=f"[green]✓ {tool_name}[/]",
                    border_style="dim green",
                    padding=(0, 1)
                ))
            else:
                console.print(Panel(
                    f"[red]{result.output}[/]",
                    title=f"[red]✗ {tool_name} failed[/]",
                    border_style="red",
                    padding=(0, 1)
                ))
            
            tool_results.append(f"Tool '{tool_name}' result:\n{result.output}")
        
        # Feed results back
        combined = "\n\n---\n\n".join(tool_results)
        messages.append({"role": "user", "content": f"Tool results:\n{combined}"})
    else:
        console.print(f"\n[yellow]⚠️ Reached max steps ({max_steps})[/]")


def httpx_error():
    import httpx
    return (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException)


def save_chat(messages: list, session_id: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = CHAT_LOGS_DIR / f"chat_{session_id}_{ts}.json"
    path.write_text(json.dumps(messages, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def show_help():
    table = Table(title="DevMind Commands", border_style="cyan")
    table.add_column("Command", style="bold yellow")
    table.add_column("Description")
    
    commands = [
        ("/help",          "Show this help"),
        ("/models",        "List available Ollama models"),
        ("/model <name>",  "Switch to a different model"),
        ("/clear",         "Clear conversation history"),
        ("/save",          "Save current chat to file"),
        ("/memory",        "Show persistent memory"),
        ("/skills",        "List available skills"),
        ("/cwd <path>",    "Change working directory"),
        ("/undo",          "Revert files modified in the last step (backup restore)"),
        ("/diff",          "Show Git diff of current changes with syntax highlighting"),
        ("/commit",        "Generate semantic commit message via Ollama and commit"),
        ("/voice",         "Speak your coding task (microphone required)"),
        ("/status",        "Show current configuration"),
        ("/exit",          "Exit DevMind"),
    ]
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    console.print(table)


def main():
    import httpx
    
    parser = argparse.ArgumentParser(description="DevMind — Local AI Coding Assistant")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--max-steps", type=int, default=10)
    args = parser.parse_args()
    
    console.print(BANNER)
    
    # Check Ollama
    with console.status("[cyan]Connecting to Ollama...[/]", spinner="dots"):
        running, models = check_ollama()
    
    if not running:
        console.print(Panel(
            "[red]❌ Ollama not running![/]\n\n"
            "1. Download: [link=https://ollama.com/download/windows]https://ollama.com/download/windows[/link]\n"
            "2. Start: [bold]ollama serve[/bold]\n"
            "3. Pull model: [bold]ollama pull qwen2.5-coder:7b[/bold]\n"
            "4. Restart DevMind",
            title="Ollama Not Found",
            border_style="red"
        ))
        sys.exit(1)
    
    # Auto-select model if requested not available
    model = args.model
    if model not in models:
        console.print(f"[yellow]⚠ Model '{model}' not found[/]")
        if models:
            model = models[0]
            console.print(f"[green]→ Using: {model}[/]")
        else:
            console.print("[red]No models installed. Run: ollama pull qwen2.5-coder:7b[/]")
            sys.exit(1)
    
    cwd = args.cwd
    
    # Create tools
    tools = create_tool_registry(confirm_callback=confirm_callback)
    
    # Init messages
    messages = [{"role": "system", "content": build_system_prompt(cwd, tools)}]
    
    console.print(Panel(
        f"[green]✅ Ready![/]\n"
        f"Model: [cyan]{model}[/]\n"
        f"Dir:   [dim]{cwd}[/]\n"
        f"Tools: [dim]{', '.join(tools.keys())}[/]\n\n"
        f"Type your task or [bold]/help[/] for commands",
        title="DevMind",
        border_style="green"
    ))
    
    # Check if memory exists
    memory = load_memory()
    if memory:
        console.print(f"[dim]💾 Memory loaded ({len(memory)} chars from MEMORY.md)[/]")
    
    session = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        style=Style.from_dict({"prompt": "bold ansicyan"}),
    )
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    while True:
        try:
            user_input = session.prompt(HTML("<ansigreen>You</ansigreen> <b>›</b> ")).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Ctrl+C caught. Type /exit to quit.[/]")
            continue
        
        if not user_input:
            continue
        
        # ── Slash commands ──────────────────────────────────────────
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""
            
            if cmd in ("/exit", "/quit", "/q"):
                path = save_chat(messages, session_id)
                console.print(f"[dim]Chat saved: {path}[/]")
                console.print("[cyan]Goodbye! Happy coding! 🚀[/]")
                break
            
            elif cmd == "/help":
                show_help()
            
            elif cmd == "/models":
                _, available = check_ollama()
                console.print("[bold cyan]📊 Working Free AI Models (Third Eye Discovery):[/]")
                
                # Try to show Third Eye categorized models
                try:
                    from third_eye import ThirdEyeSystem
                    te = ThirdEyeSystem()
                    mm = te.model_manager
                    if mm.models:
                        categories = {}
                        for m in mm.models:
                            for cat in mm.categorize(m["model"]):
                                if cat not in categories:
                                    categories[cat] = []
                                categories[cat].append(m)
                        
                        console.print(f"\n  [dim]Found {len(mm.models)} working free models:[/]")
                        for cat in ["coding", "speed", "reasoning", "general", "local"]:
                            if cat in categories:
                                cat_models = sorted(categories[cat], key=lambda x: x.get("latency_s", 999))
                                console.print(f"\n  [bold cyan]{cat.upper()}[/]:")
                                for m in cat_models:
                                    marker = "[green]✓[/]" if m["model"] == model else " "
                                    provider = m.get("provider", "?")
                                    lat = m.get("latency_s", "?")
                                    console.print(f"    {marker} [cyan]{m['model']}[/] [dim]({provider}, {lat}s)[/]")
                        
                        chain = mm.get_failover_chain()
                        console.print(f"\n  [bold]🔄 Failover chain:[/] [dim]{' → '.join(chain)[:80]}[/]")
                        continue
                except Exception:
                    pass
                
                # Fallback to basic model listing
                console.print("[bold]Available models:[/]")
                for m in available:
                    marker = "[green]✓[/]" if m == model else " "
                    console.print(f"  {marker} {m}")
            
            elif cmd == "/model":
                if arg:
                    model = arg
                    messages[0]["content"] = build_system_prompt(cwd, tools)
                    console.print(f"[green]✅ Model: {model}[/]")
                else:
                    console.print(f"Current model: {model}")
            
            elif cmd == "/clear":
                messages = [{"role": "system", "content": build_system_prompt(cwd, tools)}]
                console.print("[green]✅ Conversation cleared[/]")
            
            elif cmd == "/save":
                path = save_chat(messages, session_id)
                console.print(f"[green]✅ Saved: {path}[/]")
            
            elif cmd == "/memory":
                mem = load_memory()
                if mem:
                    console.print(Panel(mem, title="📝 Memory", border_style="cyan"))
                else:
                    console.print(f"[dim]Memory empty. File: {MEMORY_FILE}[/]")
            
            elif cmd == "/skills":
                skills = load_skills()
                if skills:
                    console.print("[bold]📚 Skills:[/]")
                    for s in skills.values():
                        console.print(f"  • [cyan]{s.name}[/]: {s.description}")
                else:
                    console.print(f"[dim]No skills. Add .md files to: {SKILLS_DIR}[/]")
            
            elif cmd == "/cwd":
                clean_path = arg.strip('\'"')
                if clean_path and Path(clean_path).is_dir():
                    cwd = clean_path
                    messages[0]["content"] = build_system_prompt(cwd, tools)
                    console.print(f"[green]✅ Working dir: {cwd}[/]")
                else:
                    console.print(f"[red]Directory not found: {clean_path}[/]")
            
            elif cmd == "/undo":
                reverted = restore_last_turn()
                if reverted:
                    for f in reverted:
                        console.print(f"[green]✅ Undo: {f}[/]")
                else:
                    console.print("[yellow]No modifications to undo in this session.[/]")
            
            elif cmd == "/diff":
                import subprocess
                try:
                    res = subprocess.run("git diff", shell=True, capture_output=True, text=True)
                    if not res.stdout.strip():
                        console.print("[yellow]No unstaged changes found. Checking staged changes...[/]")
                        res = subprocess.run("git diff --staged", shell=True, capture_output=True, text=True)
                    
                    if res.stdout.strip():
                        from rich.syntax import Syntax
                        syntax = Syntax(res.stdout, "diff", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    else:
                        console.print("[green]No changes found in repository (working tree clean).[/]")
                except Exception as e:
                    console.print(f"[red]Error displaying diff: {e}[/]")
            
            elif cmd == "/commit":
                import subprocess
                try:
                    # Check status
                    status = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True).stdout.strip()
                    if not status:
                        console.print("[green]Nothing to commit. Repository is clean.[/]")
                        continue
                    
                    # Check if there are staged changes
                    staged = subprocess.run("git diff --cached --name-only", shell=True, capture_output=True, text=True).stdout.strip()
                    if not staged:
                        ans = console.input("[yellow]No changes staged. Stage all files for commit? (y/N): [/]").strip().lower()
                        if ans in ('y', 'yes'):
                            subprocess.run("git add -A", shell=True)
                        else:
                            console.print("[red]Commit aborted.[/]")
                            continue
                    
                    # Get diff for Ollama
                    diff_data = subprocess.run("git diff --cached", shell=True, capture_output=True, text=True).stdout
                    if len(diff_data) > 10000:
                        diff_data = diff_data[:10000] + "\n... (diff truncated for length)"
                    
                    with console.status("[cyan]🤔 Analysing changes & writing commit message...[/]", spinner="dots"):
                        prompt = (
                            "You are a git expert. Write a clean, brief conventional commit message for the following git diff. "
                            "Follow this format exactly: '<type>(<scope>): <short description>' (e.g., 'feat(auth): add login validation' or 'fix(core): resolve python compilation issue'). "
                            "Do not include quotes, backticks, or any explanation. Output ONLY the single commit message line."
                            f"\n\nDIFF:\n{diff_data}"
                        )
                        commit_msg = ollama_chat([{"role": "user", "content": prompt}], model=model).strip()
                    
                    # Format check
                    commit_msg = commit_msg.replace("`", "").replace("'", "").replace('"', "").split('\n')[0].strip()
                    
                    console.print(Panel(
                        f"[bold green]Suggested Message:[/]\n{commit_msg}",
                        title="📝 Conventional Commit Builder",
                        border_style="green"
                    ))
                    
                    confirm = console.input("[yellow]Execute commit? (y/N): [/]").strip().lower()
                    if confirm in ('y', 'yes'):
                        subprocess.run(f'git commit -m "{commit_msg}"', shell=True)
                        console.print("[green]✅ Commit successful![/]")
                    else:
                        console.print("[red]Commit cancelled.[/]")
                except Exception as e:
                    console.print(f"[red]Error building commit: {e}[/]")
            
            elif cmd == "/voice":
                try:
                    import speech_recognition as sr
                    recognizer = sr.Recognizer()
                    with sr.Microphone() as source:
                        console.print("\n[cyan]🎙️ Listening (speak your command now)...[/]")
                        recognizer.adjust_for_ambient_noise(source, duration=1)
                        audio = recognizer.listen(source, timeout=8)
                        console.print("[cyan]⏳ Transcribing speech...[/]")
                        text = recognizer.recognize_google(audio)
                        console.print(f"[green]You (Voice) ›[/] {text}\n")
                        run_agent_loop(text, messages, tools, model, max_steps=args.max_steps)
                except ImportError:
                    console.print(
                        "[red]❌ SpeechRecognition or PyAudio is not installed![/]\n"
                        "Please run: [bold]pip install SpeechRecognition pyaudio[/bold] to use voice commands."
                    )
                except sr.WaitTimeoutError:
                    console.print("[red]❌ Speech input timed out (no audio detected).[/]")
                except Exception as e:
                    console.print(f"[red]❌ Speech recognition failed: {e}[/]")
            
            elif cmd == "/status":
                console.print(Panel(
                    f"Model: {model}\nDir: {cwd}\n"
                    f"Messages: {len(messages)}\n"
                    f"Memory: {MEMORY_FILE}\nSkills: {SKILLS_DIR}",
                    title="Status"
                ))
            
            else:
                console.print(f"[red]Unknown command. Type /help[/]")
            
            continue
        
        # ── Agent loop ──────────────────────────────────────────────
        try:
            run_agent_loop(user_input, messages, tools, model, max_steps=args.max_steps)
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Interrupted[/]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


if __name__ == "__main__":
    main()
