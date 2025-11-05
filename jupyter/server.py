import os
import tomllib
import openai
import subprocess
import nbformat
import threading
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    raise FileNotFoundError(f".env MUST exist in directory {env_path.parent}")

# Load config
config_path = Path(__file__).parent / "config.toml"
with config_path.open("rb") as f:
    config = tomllib.load(f)

# Initialize OpenAI client
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "dummy"),
    base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:8000/v1")
)

# Initialize Working Space and deep_analyze.ipynb file
workspace_dir = Path(__file__).parent / "workspace"
workspace_dir.mkdir(exist_ok=True)
notebook = nbformat.v4.new_notebook()
notebook.cells.append(nbformat.v4.new_markdown_cell("The Workspace of Deep Analyze"))
with open(workspace_dir / "deep_analyze.ipynb", "w", encoding="utf-8") as f:
    nbformat.write(notebook, f)

# Initialize Jupyter Process
jupyter_port = config.get("JUPYTER_PORT", 8888)
cmd = [
    "uv", "run", "jupyter", "lab",
    "--ServerApp.root_dir", str(workspace_dir),
    "--port", str(jupyter_port),
]
jupyter_process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)
def start():
    for line in jupyter_process.stdout:
        pass

output_thread = threading.Thread(target=start)
output_thread.daemon = True
output_thread.start()