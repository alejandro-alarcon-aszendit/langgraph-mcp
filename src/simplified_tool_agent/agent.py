import asyncio
import os
from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp import ClientSession
from rich.console import Console
from mcp.types import InitializeResult
from dotenv import load_dotenv
#from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
load_dotenv()

console = Console()

# Works with any tool capable LLM
#llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
llm = ChatOpenAI(model="gpt-4o")
# llm = ChatOllama(model="llama3.2:latest")

SERVER_CONFIGS = {
        "brave-search": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {
                "BRAVE_API_KEY": os.environ.get("BRAVE_API_KEY"),  # get a free key from BRAVE
                "PATH": os.environ.get("PATH"),  # adding PATH helps MCP spawned process find things your path
            },
        },
        "google-calendar": {
            "command": "/usr/local/bin/node",  # Use absolute path to node executable
            "transport": "stdio",
            "args": [
                "/Users/aleibz/langgraph-mcp/google-calendar/build/index.js"
            ],
            "env": {
                "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID"),
                "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "GOOGLE_REDIRECT_URI": os.environ.get("GOOGLE_REDIRECT_URI"),
                "GOOGLE_REFRESH_TOKEN": os.environ.get("GOOGLE_REFRESH_TOKEN"),
                "PATH": os.environ.get("PATH")  # Include PATH to help find dependencies
            }
        }
}

@asynccontextmanager
async def amain():
    """Async main function to connect to MCP."""
    async with MultiServerMCPClient(SERVER_CONFIGS) as client:
        # Get the session from the client for the "brave-search" server
        llm_tools = client.get_tools()

        llm_with_tools = llm.bind_tools(llm_tools)
        sys_msg = SystemMessage(content="You are a helpful assistant. Use available tools to assist the user. \
                                You can use the google calendar tool to get the user's calendar events.")

        # Define assistant function
        def assistant(state: MessagesState):
            return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

        # Build the graph
        builder = StateGraph(MessagesState)
        builder.add_node("assistant", assistant)
        builder.add_node("tools", ToolNode(llm_tools))

        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant",
            tools_condition,
        )
        builder.add_edge("tools", "assistant")

        # Compile the graph before yielding
        graph = builder.compile()
        yield graph


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()