from fastmcp.client.transports import StdioTransport
import asyncio
from fastmcp import Client
from fastmcp.client.client import CallToolResult
from mcp.types import TextContent, ImageContent

import re
import time

transport = StdioTransport(
    command="npx",
    args=["mcp-remote", "http://127.0.0.1:8888/mcp"],
)

client = Client(transport)

def convert_to_backend_format(mcp_result: CallToolResult):
    """
    Convert a CallToolResult object to the backend.py Execute API format.
    
    Args:
        mcp_result: MCP's CallToolResult object
    
    Returns:
        A dictionary in the format expected by backend.py Execute API
    """
    # 使用原有的convert_mcp_openai函数获取文本内容
    text = []
    for content in mcp_result.content:
        if isinstance(content, TextContent):
            text.append(content.text)
        elif isinstance(content, ImageContent):
            text.append(f"[IMG OUTPUT]")
        else:
            text.append(f"[UNKNOWN CONTENT TYPE]")
    
    # 将文本内容合并为一个字符串
    result_text = "\n".join(text) if text else ""
    
    # 返回符合OpenAI API格式的字典
    return {"role": "assistant", "content": result_text}

async def create_notebook():
    async with client:
        await client.call_tool("use_notebook", {
            "notebook_name": "deep_analyze",
            "notebook_path": "test.ipynb",
            "mode": "connect"
        })

async def insert_cell(cell_index, cell_type, cell_source):
    async with client:
        result = await client.call_tool("insert_cell", {
            "cell_index": cell_index,
            "cell_type": cell_type,
            "cell_source": cell_source,
        })
        content = result.content[0].text
        match = re.search(r"Cell inserted successfully at index (\d+)", content)
        actual_index = int(match.group(1)) if match else None
    return actual_index

async def append_execute_cell(cell_source, timeout=90):
    async with client:
        index = await insert_cell(-1, "code", cell_source)

        result = await client.call_tool("execute_cell", {
            "cell_index": index,
            "timeout": timeout
        })

    return convert_to_backend_format(result)

async def main():
    await create_notebook()
    print("Hello World!\n\n")
    
    # 执行代码并获取backend.py格式的结果
    result = await append_execute_cell("print('hello world')")
    print(result)  # 现在会打印符合backend.py格式的字典
    
    time.sleep(1)
    print("Cell index:")
    print(await insert_cell(-1, "markdown", "Good Notebook"))
    time.sleep(1)
    print("IMG:")
    code = """
import matplotlib.pyplot as plt
import numpy as np

print("sin(x)")

x = np.linspace(0, 10, 100)
plt.plot(x, np.sin(x))
plt.show()
    """
    img_result = await append_execute_cell(code)
    print(img_result)  # 包含[IMG OUTPUT]的backend.py格式结果
    
    time.sleep(1)
    print("Goodbye World!\n\n")
    goodbye_result = await append_execute_cell("print('goodbye world')")
    print(goodbye_result)  # backend.py格式结果

if __name__ == "__main__":
    asyncio.run(main())
