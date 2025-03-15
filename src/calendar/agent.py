# ---- calendar_module.py ----
import os
import pathlib
import logging
import asyncio
from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4o")

@asynccontextmanager
async def calendar_graph_module():
    # Build the absolute path to the MCP server index.js
    async with MultiServerMCPClient({
        "calendar": {
            "command": "node",
            "args": ["/Users/aleibz/langgraph-mcp/google-calendar-mcp/build/index.js"],
            "transport": "stdio"
        }
    }) as client:
        tools = client.get_tools()
        agent = create_react_agent(llm, tools)
        yield agent
