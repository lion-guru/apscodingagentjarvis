"""
JARVIS Voice Core — Real-Time Voice Command & Hands-Free Assistant
Parses voice audio inputs into DevMind actionable tool commands.
"""
import re

class JarvisVoiceCore:
    def __init__(self):
        self.trigger_word = "jarvis"

    def parse_voice_command(self, raw_transcript: str) -> dict:
        """Parse raw speech transcript into structured tool intent."""
        clean = raw_transcript.strip().lower()
        
        # Check if JARVIS trigger word is present
        triggered = self.trigger_word in clean
        command_body = clean.replace(self.trigger_word, "").strip() if triggered else clean
        
        # Intent mapping
        intent = "general_chat"
        action = "none"
        
        if any(w in command_body for w in ["security", "vulnerab", "audit"]):
            intent = "security_review"
            action = "scan_diff"
        elif any(w in command_body for w in ["metrics", "insights", "loc"]):
            intent = "code_insights"
            action = "analyze"
        elif any(w in command_body for w in ["swarm", "team", "agent team"]):
            intent = "team_swarm"
            action = "create"
        elif any(w in command_body for w in ["plan", "design"]):
            intent = "plan_mode"
            action = "create"
        elif any(w in command_body for w in ["commit", "push", "git"]):
            intent = "git_sync"
            action = "commit_push"

        return {
            "triggered": triggered,
            "raw": raw_transcript,
            "parsed_command": command_body,
            "intent": intent,
            "action": action
        }

# Global Instance
voice_core = JarvisVoiceCore()
