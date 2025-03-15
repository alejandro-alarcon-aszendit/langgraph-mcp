# ---- LangGraph Module Definition: integrate MCP tools ----
from contextlib import asynccontextmanager
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# Define an async context manager for the LangGraph module
@asynccontextmanager
async def math_graph_module():
    # Connect to the MCP Math server using the adapter
    async with MultiServerMCPClient({
        "math": {  # Identifier for our math server
            "command": "python", 
            "args": ["/Users/aleibz/langgraph-mcp/src/base/math_server.py"],  # path to the MCP server script
            "transport": "stdio"
        }
    }) as client:
        # Once connected, retrieve the available tools from the MCP server
        tools = client.get_tools()  # auto-discovers all tools from the "math" server
        # Create an LLM agent (ReAct pattern) that can use these tools
        llm = ChatOpenAI(model="gpt-4")  # or any Chat model configured for LangGraph
        agent = create_react_agent(llm, tools)
        # Yield the agent so LangGraph can use it as part of the workflow
        yield agent
