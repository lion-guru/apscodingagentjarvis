"""
DevMind Deploy Panel
One-click deploy panel for web UI.
Supports Docker, Cloud, and local deployment targets.
"""
import json
from pathlib import Path
from datetime import datetime

DEPLOY_DIR = Path.home() / ".devmind" / "deploy"

class DeployPanel:
    def __init__(self):
        DEPLOY_DIR.mkdir(parents=True, exist_ok=True)

    def deploy_docker(self, workspace: str = "E:\\coding-assistant",
                       image_name: str = "devmind-app") -> dict:
        """Generate Docker deployment configuration."""
        docker_config = {
            "name": image_name,
            "workspace": workspace,
            "dockerfile": f"""FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "server.py"]
""",
            "docker_compose": {
                "version": "3.8",
                "services": {
                    "devmind": {
                        "build": ".",
                        "ports": {"8000": "8000"},
                        "volumes": [f"{workspace}:/app"],
                        "environment": {
                            "OLLAMA_HOST": "http://ollama:11434",
                            "DEVMIND_WORKSPACE": "/app",
                        }
                    }
                }
            }
        }

        deploy_file = DEPLOY_DIR / "docker_config.json"
        deploy_file.write_text(json.dumps(docker_config, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "deploy": docker_config}

    def deploy_cloud(self, provider: str = "aws",
                      workspace: str = "E:\\coding-assistant") -> dict:
        """Generate cloud deployment configuration."""
        config = {
            "provider": provider,
            "workspace": workspace,
            "generated_at": datetime.now().isoformat(),
            "targets": {
                "aws": {"service": "Elastic Beanstalk", "region": "us-east-1"},
                "gcp": {"service": "Cloud Run", "region": "us-central1"},
                "azure": {"service": "App Service", "region": "eastus"},
            }
        }

        deploy_file = DEPLOY_DIR / "cloud_config.json"
        deploy_file.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "deploy": config}

    def deploy_local(self, workspace: str = "E:\\coding-assistant") -> dict:
        """Generate local deployment configuration."""
        config = {
            "type": "local",
            "workspace": workspace,
            "command": "python server.py",
            "port": 8000,
            "generated_at": datetime.now().isoformat(),
        }

        deploy_file = DEPLOY_DIR / "local_config.json"
        deploy_file.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "deploy": config}

    def list_deployments(self) -> list[dict]:
        """List all deployment configurations."""
        deployments = []
        if DEPLOY_DIR.exists():
            for f in DEPLOY_DIR.glob("*.json"):
                try:
                    deployments.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        return deployments


deploy_panel = DeployPanel()

# Module-level wrapper functions for server.py compatibility
def deploy_docker(workspace="E:\\coding-assistant"):
    return deploy_panel.deploy_docker(workspace)

def deploy_cloud(provider="aws", workspace="E:\\coding-assistant"):
    return deploy_panel.deploy_cloud(provider, workspace)

def deploy_local(workspace="E:\\coding-assistant"):
    return deploy_panel.deploy_local(workspace)

def list_deployments():
    return deploy_panel.list_deployments()