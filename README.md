# LangGraph MCP Examples & Testing

This repository contains examples, tests, and implementations of [LangGraph](https://github.com/langchain-ai/langgraph) with [Model Context Protocol (MCP)](https://github.com/microsoft/modelcontextprotocol) server integrations. It demonstrates how to build complex agentic workflows with external tools and services through MCP.

## Overview

LangGraph is a library for building stateful, multi-actor applications with LLMs. This repository showcases different patterns and implementations with a special focus on:

- Integration with external tools via MCP servers
- Building stateful, memory-aware agents
- Task management applications using Google Calendar integration
- Creating robust, scalable agent architectures

## Repository Structure

- `src/langgraph_assistant/`: Task management assistant with memory capabilities and calendar integration
- `src/simplified_tool_agent/`: Minimal example of a LangGraph agent with MCP tools
- `src/tool_node/`: Advanced tool integration patterns using custom MCP tool nodes
- `google-calendar/`: MCP server implementation for Google Calendar

## Key Components

### Task mAIstro

A comprehensive task management assistant that:
- Maintains a persistent ToDo list
- Integrates with Google Calendar for scheduling
- Automatically updates tasks based on calendar events
- Uses memory to track user preferences

### Tool Agents

Multiple implementations of tool-using agents with different levels of complexity:
- Simple tool routing
- Advanced MCP tool node implementations
- Error handling and tool execution flows

## Setup & Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ (for MCP servers)
- Google Calendar API credentials (for calendar examples)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/langgraph-mcp.git
   cd langgraph-mcp
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Calendar MCP server:
   ```bash
   cd google-calendar
   npm install
   npm run build
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env` (if available)
   - Add your API keys and credentials (see Configuration section)

## Configuration

Create a `.env` file in the root directory with the following variables:

```
# LangSmith (optional, for tracing)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=your_project_name

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Google Calendar
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost
GOOGLE_REFRESH_TOKEN=your_refresh_token

# Brave Search (optional)
BRAVE_API_KEY=your_brave_api_key
```

### Getting Google Calendar Credentials

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Calendar API
3. Create OAuth credentials
4. Use the `getToken.cjs` script to generate a refresh token:
   ```bash
   cd google-calendar
   node getToken.cjs
   ```

## Running Examples

### Task mAIstro

```bash
python -m src.langgraph_assistant.main
```

### Simplified Tool Agent

```bash
python -m src.simplified_tool_agent.main
```

### Advanced Tool Node

```bash
python -m src.tool_node.main
```

## Testing

This repository includes various test files to demonstrate how to test LangGraph implementations with MCP server integrations.

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/test_task_maistro.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for the foundational LLM tooling
- [LangGraph](https://github.com/langchain-ai/langgraph) for the graph execution framework
- [Model Context Protocol](https://github.com/microsoft/modelcontextprotocol) for the tool execution standard
