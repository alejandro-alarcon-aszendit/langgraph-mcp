#!/usr/bin/env python3

import asyncio
from src.calendar.agent import calendar_graph_module
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        print("Starting calendar graph module test...")
        async with calendar_graph_module() as graph:
            print(f"Successfully created graph: {graph.name}")
            print(f"Retrieved {len(graph.tools)} tools from the calendar server:")
            for tool in graph.tools:
                print(f"- {tool.name}: {tool.description}")
            
            # Test the graph's invoke method
            result = await graph.ainvoke({"query": "What calendar tools are available?"})
            print(f"\nGraph invocation result: {result['message']}")
            
            print("\nTest completed successfully!")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 