#!/usr/bin/env python3

import asyncio
import subprocess
import sys
import json
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_mcp_server():
    # Path to the MCP server
    workspace_root = Path(__file__).parent.absolute()
    mcp_server_path = workspace_root / "google-calendar-mcp" / "build" / "index.js"
    
    logger.info(f"Starting server at: {mcp_server_path}")
    
    # Start the MCP server as a subprocess
    proc = await asyncio.create_subprocess_exec(
        "node", str(mcp_server_path),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Wait a bit for the server to initialize
    logger.info("Waiting for server to initialize...")
    
    # Initialize message based on current SDK v1.7.0
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            },
            "capabilities": {}
        }
    }
    
    # Convert to JSON and send
    init_str = json.dumps(init_message) + "\n"
    logger.info(f"Sending initialize request: {init_str}")
    proc.stdin.write(init_str.encode())
    await proc.stdin.drain()
    
    # Read response with a timeout
    try:
        async with asyncio.timeout(5):
            line = await proc.stdout.readline()
            if not line:
                logger.error("No response received from server")
                return
            
            logger.info(f"Received response: {line.decode().strip()}")
            
            # Send "initialized" notification
            initialized_msg = {
                "jsonrpc": "2.0",
                "method": "initialized",
                "params": {}
            }
            init_str = json.dumps(initialized_msg) + "\n"
            logger.info(f"Sending initialized notification: {init_str}")
            proc.stdin.write(init_str.encode())
            await proc.stdin.drain()
            
            # Send tools/list request (correct method name based on server code)
            list_tools_msg = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            list_tools_str = json.dumps(list_tools_msg) + "\n"
            logger.info(f"Sending listTools request: {list_tools_str}")
            proc.stdin.write(list_tools_str.encode())
            await proc.stdin.drain()
            
            # Read response
            line = await proc.stdout.readline()
            if not line:
                logger.error("No response received from listTools request")
                return
            
            logger.info(f"Received listTools response: {line.decode().strip()}")
            
    except asyncio.TimeoutError:
        logger.error("Timed out waiting for server response")
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        try:
            proc.terminate()
            await proc.wait()
        except:
            logger.exception("Error during cleanup")

if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_server())
    except Exception as e:
        logger.exception("Unhandled exception")
        sys.exit(1) 