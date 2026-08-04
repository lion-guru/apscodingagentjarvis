from setuptools import setup, find_packages

setup(
    name="devmind",
    version="1.0.0",
    description="DevMind - AI-Powered Web IDE with local LLM integration",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "websockets>=12.0",
        "httpx>=0.25.0",
        "pydantic>=2.0",
        "jinja2>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "devmind=server:main",
        ],
    },
)