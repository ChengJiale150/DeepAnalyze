import os
import re
import tomllib
import openai
import subprocess
import nbformat
import threading
from pathlib import Path
from dotenv import load_dotenv
from tools import (
    list_workspace_files,
    connect_notebook,
    append_execute_cell,
    insert_cell
)

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
start_jupyter = config.get("START_JUPYTER", False)
jupyter_process = None
if start_jupyter:
    cmd = [
        "uv", "run", "jupyter", "lab",
        "--ServerApp.root_dir", workspace_dir.as_posix(),
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

async def bot_stream(messages):
    """
    Bot streaming function that processes messages and executes code in Jupyter notebook.
    This is adapted from demo/backend.py but modified to work with Jupyter notebook.
    """
    # Connect to notebook
    mcp_client = await connect_notebook(jupyter_port)
    
    # Get file context
    file_info = await list_workspace_files(mcp_client)
    
    # Process messages
    if messages and messages[0]["role"] == "assistant":
        messages = messages[1:]
    
    if messages and messages[-1]["role"] == "user":
        user_message = messages[-1]["content"]
        if file_info:
            messages[-1]["content"] = f"# Instruction\n{user_message}\n\n# Data\n{file_info}"
        else:
            messages[-1]["content"] = f"# Instruction\n{user_message}"
    
    assistant_reply = ""
    finished = False
    
    while not finished:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "DeepAnalyze-8B"),
            messages=messages,
            temperature=0.4,
            stream=True,
            extra_body={
                "add_generation_prompt": False,
                "stop_token_ids": [151676, 151645],
                "max_new_tokens": 32768,
            },
        )
        
        cur_res = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                delta = chunk.choices[0].delta.content
                cur_res += delta
                assistant_reply += delta
                yield assistant_reply
            if "</Answer>" in cur_res:
                finished = True
                break
                
        if chunk.choices[0].finish_reason == "stop" and not finished:
            if not cur_res.endswith("</Code>"):
                cur_res += "</Code>"
                assistant_reply += "</Code>"
            yield assistant_reply
            
        if "</Code>" in cur_res and not finished:
            messages.append({"role": "assistant", "content": cur_res})
            
            # Extract code from <Code> tag
            code_match = re.search(r"<Code>(.*?)</Code>", cur_res, re.DOTALL)
            if code_match:
                code_content = code_match.group(1).strip()
                md_match = re.search(r"```(?:python)?(.*?)```", code_content, re.DOTALL)
                code_str = md_match.group(1).strip() if md_match else code_content
                
                # Execute code in Jupyter notebook
                exe_output = await append_execute_cell(mcp_client, code_str)
                exe_str = f"\n<Execute>\n```\n{exe_output}\n```\n</Execute>\n"
                assistant_reply += exe_str
                yield assistant_reply
                messages.append({"role": "execute", "content": exe_output})
        
        # Process other tags (Analyze, Understand, Answer) and add them as markdown cells
        for tag in ["Analyze", "Understand", "Answer"]:
            tag_pattern = f"<{tag}>(.*?)</{tag}>"
            tag_match = re.search(tag_pattern, cur_res, re.DOTALL)
            if tag_match:
                tag_content = tag_match.group(1).strip()
                await insert_cell(mcp_client, -1, cell_source=tag_content, cell_type="markdown")
                
                # Add to assistant reply for display
                md_str = f"\n<{tag}>\n{tag_content}\n</{tag}>\n"
                assistant_reply += md_str
                yield assistant_reply
    
    yield assistant_reply





