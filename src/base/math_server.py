# ---- MCP Server: math_server.py ----
from mcp.server.fastmcp import FastMCP

# Initialize an MCP server named "MathServer"
mcp = FastMCP("MathServer")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

if __name__ == "__main__":
    # Run the MCP server (using stdio transport for this example)
    mcp.run(transport="stdio")
