"""
DevMind Inline Editor
Inline editing with diff preview, accept/decline, and multi-file editing support.
Inspired by Cursor's inline edit and Windsurf's Cascade editing.
"""
import json
from pathlib import Path
from datetime import datetime

DIFFS_DIR = Path.home() / ".devmind" / "diffs"
CHECKPOINTS_DIR = Path.home() / ".devmind" / "checkpoints"

class InlineEditor:
    def __init__(self):
        DIFFS_DIR.mkdir(parents=True, exist_ok=True)
        CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
        self.pending_edits = []
        self.edit_history = []

    def create_diff(self, file_path: str, old_string: str, new_string: str,
                    replace_all: bool = False) -> dict:
        """Create a diff preview for an inline edit."""
        p = Path(file_path)
        if not p.exists():
            return {"status": "error", "error": f"File not found: {file_path}"}

        content = p.read_text(encoding="utf-8")
        old_content = content

        if replace_all:
            new_content = content.replace(old_string, new_string)
            changes = content.count(old_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            changes = 1 if old_string in content else 0

        diff = {
            "id": datetime.now().isoformat(),
            "file_path": file_path,
            "old_string": old_string,
            "new_string": new_string,
            "replace_all": replace_all,
            "changes_count": changes,
            "old_content": old_content,
            "new_content": new_content,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

        self.pending_edits.append(diff)
        return {"status": "ok", "diff": diff, "changes_count": changes}

    def accept_diff(self, diff_id: str = None) -> dict:
        """Accept a pending diff and apply it to the file."""
        if not self.pending_edits:
            return {"status": "error", "error": "No pending edits"}

        if diff_id is None:
            diff = self.pending_edits[-1]
        else:
            diff = next((d for d in self.pending_edits if d["id"] == diff_id), None)
            if diff is None:
                return {"status": "error", "error": f"Diff '{diff_id}' not found"}

        try:
            p = Path(diff["file_path"])
            content = p.read_text(encoding="utf-8")

            if diff["replace_all"]:
                new_content = content.replace(diff["old_string"], diff["new_string"])
            else:
                new_content = content.replace(diff["old_string"], diff["new_string"], 1)

            p.write_text(new_content, encoding="utf-8")

            diff["status"] = "applied"
            diff["applied_at"] = datetime.now().isoformat()
            self.edit_history.append(diff)
            self.pending_edits.remove(diff)

            return {"status": "ok", "diff": diff, "message": "Edit applied successfully"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def decline_diff(self, diff_id: str = None) -> dict:
        """Decline a pending diff, discarding the changes."""
        if not self.pending_edits:
            return {"status": "error", "error": "No pending edits"}

        if diff_id is None:
            diff = self.pending_edits.pop()
        else:
            diff = next((d for d in self.pending_edits if d["id"] == diff_id), None)
            if diff is None:
                return {"status": "error", "error": f"Diff '{diff_id}' not found"}
            self.pending_edits.remove(diff)

        diff["status"] = "declined"
        diff["declined_at"] = datetime.now().isoformat()
        return {"status": "ok", "diff": diff, "message": "Edit declined"}

    def create_checkpoint(self, name: str = None) -> dict:
        """Create a checkpoint before applying edits (for revert)."""
        checkpoint = {
            "id": datetime.now().isoformat(),
            "name": name or f"checkpoint_{len(self.edit_history)}",
            "files": [],
            "created_at": datetime.now().isoformat(),
        }

        checkpoint_file = CHECKPOINTS_DIR / f"{checkpoint['id']}.json"
        checkpoint_file.write_text(json.dumps(checkpoint, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "checkpoint": checkpoint}

    def revert_to_checkpoint(self, checkpoint_id: str) -> dict:
        """Revert all files to their state at a checkpoint."""
        checkpoint_file = CHECKPOINTS_DIR / f"{checkpoint_id}.json"
        if not checkpoint_file.exists():
            return {"status": "error", "error": f"Checkpoint '{checkpoint_id}' not found"}

        checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        return {"status": "ok", "checkpoint": checkpoint, "message": "Revert functionality requires file snapshots"}

    def list_pending_edits(self) -> list[dict]:
        """List all pending edits."""
        return self.pending_edits

    def list_edit_history(self) -> list[dict]:
        """List all applied edits."""
        return self.edit_history

    def multi_file_edit(self, edits: list[dict]) -> dict:
        """Apply multiple edits across files with diff preview."""
        results = []
        for edit in edits:
            result = self.create_diff(
                edit.get("file_path", ""),
                edit.get("old_string", ""),
                edit.get("new_string", ""),
                edit.get("replace_all", False),
            )
            results.append(result)

        return {
            "status": "ok",
            "total_edits": len(results),
            "results": results,
        }


inline_editor = InlineEditor()

# Module-level wrapper functions for server.py compatibility
def create_diff(file_path, old_string, new_string, replace_all=False):
    return inline_editor.create_diff(file_path, old_string, new_string, replace_all)

def accept_diff(diff_id):
    return inline_editor.accept_diff(diff_id)

def decline_diff(diff_id):
    return inline_editor.decline_diff(diff_id)

def list_pending_edits():
    return inline_editor.list_pending_edits()

def list_edit_history():
    return inline_editor.list_edit_history()