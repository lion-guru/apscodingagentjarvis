"""
DevMind Breadcrumb Navigation
Breadcrumb navigation for file paths in the IDE.
"""
from pathlib import Path

class BreadcrumbNav:
    def __init__(self, workspace: str = "E:\\coding-assistant"):
        self.workspace = Path(workspace)

    def get_breadcrumbs(self, file_path: str) -> list[dict]:
        """Get breadcrumb navigation for a file path."""
        path = Path(file_path)
        breadcrumbs = []
        current = path

        while current != current.parent:
            breadcrumbs.append({
                "name": current.name,
                "path": str(current),
                "is_file": current == path,
                "exists": current.exists(),
            })
            current = current.parent

        breadcrumbs.reverse()
        return breadcrumbs

    def get_path_segments(self, file_path: str) -> list[str]:
        """Get path segments for display."""
        path = Path(file_path)
        return [seg for seg in path.parts]

    def shorten_path(self, file_path: str, max_segments: int = 3) -> str:
        """Shorten a file path for display in the UI."""
        path = Path(file_path)
        parts = list(path.parts)
        if len(parts) <= max_segments:
            return str(path)
        return ".../" + "/".join(parts[-max_segments:])


breadcrumb_nav = BreadcrumbNav()