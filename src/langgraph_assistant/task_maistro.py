import uuid
import os
from datetime import datetime
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

from trustcall import create_extractor

from typing import Literal, Optional, TypedDict

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import merge_message_runs
from langchain_core.messages import SystemMessage, HumanMessage

from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode

import configuration

calendar_tools = []

# Load environment variables
load_dotenv()

## Utilities 
# Inspect the tool calls for Trustcall
class Spy:
    def __init__(self):
        self.called_tools = []

    def __call__(self, run):
        q = [run]
        while q:
            r = q.pop()
            if r.child_runs:
                q.extend(r.child_runs)
            if r.run_type == "chat_model":
                self.called_tools.append(
                    r.outputs["generations"][0][0]["message"]["kwargs"]["tool_calls"]
                )

# Extract information from tool calls for both patches and new memories in Trustcall
def extract_tool_info(tool_calls, schema_name="Memory"):
    """Extract information from tool calls for both patches and new memories.
    
    Args:
        tool_calls: List of tool calls from the model
        schema_name: Name of the schema tool (e.g., "Memory", "ToDo", "Profile")
    """
    # Initialize list of changes
    changes = []
    
    for call_group in tool_calls:
        for call in call_group:
            if call['name'] == 'PatchDoc':
                # Check if there are any patches
                if call['args']['patches']:
                    changes.append({
                        'type': 'update',
                        'doc_id': call['args']['json_doc_id'],
                        'planned_edits': call['args']['planned_edits'],
                        'value': call['args']['patches'][0]['value']
                    })
                else:
                    # Handle case where no changes were needed
                    changes.append({
                        'type': 'no_update',
                        'doc_id': call['args']['json_doc_id'],
                        'planned_edits': call['args']['planned_edits']
                    })
            elif call['name'] == schema_name:
                changes.append({
                    'type': 'new',
                    'value': call['args']
                })

    # Format results as a single string
    result_parts = []
    for change in changes:
        if change['type'] == 'update':
            result_parts.append(
                f"Document {change['doc_id']} updated:\n"
                f"Plan: {change['planned_edits']}\n"
                f"Added content: {change['value']}"
            )
        elif change['type'] == 'no_update':
            result_parts.append(
                f"Document {change['doc_id']} unchanged:\n"
                f"{change['planned_edits']}"
            )
        else:
            result_parts.append(
                f"New {schema_name} created:\n"
                f"Content: {change['value']}"
            )
    
    return "\n\n".join(result_parts)

# Google Calendar MCP server configuration
SERVER_CONFIGS = {
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

## Schema definitions

# ToDo schema
class ToDo(BaseModel):
    task: str = Field(description="The task to be completed.")
    time_to_complete: Optional[int] = Field(description="Estimated time to complete the task (minutes).")
    deadline: Optional[datetime] = Field(
        description="When the task needs to be completed by (if applicable)",
        default=None
    )
    solutions: list[str] = Field(
        description="List of specific, actionable solutions (e.g., specific ideas, service providers, or concrete options relevant to completing the task)",
        min_items=1,
        default_factory=list
    )
    status: Literal["not started", "in progress", "done", "archived"] = Field(
        description="Current status of the task",
        default="not started"
    )

## Initialize the model and tools

# Update memory tool
class UpdateMemory(TypedDict):
    """ Decision on what memory type to update """
    update_type: Literal['todo', 'instructions']

# Initialize the model
model = ChatOpenAI(model="gpt-4o", temperature=0)

## Prompts 

# Chatbot instruction for choosing what to update and what tools to call 
MODEL_SYSTEM_MESSAGE = """{task_maistro_role} 

You have a long term memory which keeps track of two things:
1. The user's ToDo list
2. General instructions for updating the ToDo list

You also have access to the user's Google Calendar through calendar tools.

Here is the current ToDo List (may be empty if no tasks have been added yet):
<todo>
{todo}
</todo>

Here are the current user-specified preferences for updating the ToDo list (may be empty if no preferences have been specified yet):
<instructions>
{instructions}
</instructions>

Here are your instructions for reasoning about the user's messages:

1. Reason carefully about the user's messages as presented below. 

2. Decide whether any of the your long-term memory should be updated:
- If tasks are mentioned, update the ToDo list by calling UpdateMemory tool with type `todo`
- If the user has specified preferences for how to update the ToDo list, update the instructions by calling UpdateMemory tool with type `instructions`

3. Tell the user that you have updated your memory, if appropriate:
- Tell the user them when you update the todo list
- Do not tell the user that you have updated instructions

4. To help the user with scheduling and task management:
- Use calendar tools to check the user's schedule when appropriate
- When adding tasks with deadlines, check if there are calendar conflicts
- Suggest suitable times for tasks based on the user's calendar availability
- VERY IMPORTANT: Whenever you retrieve calendar events using calendar tools, automatically call UpdateMemory with type `todo` to update the ToDo list with relevant tasks based on those events
- When calendar events are retrieved, create or update corresponding ToDo items with matching deadlines and details
- Add preparation tasks for important meetings or events (e.g., "Prepare for [meeting]" tasks before scheduled meetings)

5. Err on the side of updating the todo list. No need to ask for explicit permission.

6. Respond naturally to user user after a tool call was made to save memories, or if no tool call was made."""

# Trustcall instruction
TRUSTCALL_INSTRUCTION = """Reflect on following interaction. 

Use the provided tools to retain any necessary memories about the user. 

Use parallel tool calling to handle updates and insertions simultaneously.

System Time: {time}"""

# Instructions for updating the ToDo list
CREATE_INSTRUCTIONS = """Reflect on the following interaction.

Based on this interaction, update your instructions for how to update ToDo list items. Use any feedback from the user to update how they like to have items added, etc.

Your current instructions are:

<current_instructions>
{current_instructions}
</current_instructions>"""

## Node definitions

def task_mAIstro(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """Load memories from the store and use them to personalize the chatbot's response."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    task_maistro_role = configurable.task_maistro_role

    # Retrieve people memory from the store
    namespace = ("todo", todo_category, user_id)
    memories = store.search(namespace)
    todo = "\n".join(f"{mem.value}" for mem in memories)

    # Retrieve custom instructions
    namespace = ("instructions", todo_category, user_id)
    memories = store.search(namespace)
    if memories:
        instructions = memories[0].value
    else:
        instructions = ""
    
    system_msg = MODEL_SYSTEM_MESSAGE.format(task_maistro_role=task_maistro_role, todo=todo, instructions=instructions)

    # Bind calendar tools to the model if available
    global calendar_tools
    print("Length of calendar tools: ", len(calendar_tools))
    if calendar_tools:
        all_tools = [UpdateMemory] + calendar_tools
        model_with_tools = model.bind_tools(all_tools, parallel_tool_calls=True)
    else:
        model_with_tools = model.bind_tools([UpdateMemory], parallel_tool_calls=False)

    # Respond using memory as well as the chat history
    response = model_with_tools.invoke([SystemMessage(content=system_msg)]+state["messages"])

    return {"messages": [response]}

def update_todos(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflect on the chat history and update the memory collection."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category

    # Define the namespace for the memories
    namespace = ("todo", todo_category, user_id)

    # Retrieve the most recent memories for context
    existing_items = store.search(namespace)

    # Format the existing memories for the Trustcall extractor
    tool_name = "ToDo"
    existing_memories = ([(existing_item.key, tool_name, existing_item.value)
                          for existing_item in existing_items]
                          if existing_items
                          else None
                        )

    # Merge the chat history and the instruction
    TRUSTCALL_INSTRUCTION_FORMATTED=TRUSTCALL_INSTRUCTION.format(time=datetime.now().isoformat())
    updated_messages=list(merge_message_runs(messages=[SystemMessage(content=TRUSTCALL_INSTRUCTION_FORMATTED)] + state["messages"][:-1]))

    # Initialize the spy for visibility into the tool calls made by Trustcall
    spy = Spy()
    
    # Create the Trustcall extractor for updating the ToDo list 
    todo_extractor = create_extractor(
    model,
    tools=[ToDo],
    tool_choice=tool_name,
    enable_inserts=True
    ).with_listeners(on_end=spy)

    # Invoke the extractor
    result = todo_extractor.invoke({"messages": updated_messages, 
                                         "existing": existing_memories})

    # Save save the memories from Trustcall to the store
    for r, rmeta in zip(result["responses"], result["response_metadata"]):
        store.put(namespace,
                  rmeta.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )
        
    # Respond to the tool call made in task_mAIstro, confirming the update    
    tool_calls = state['messages'][-1].tool_calls
    tool_call_id = tool_calls[0].get('id')

    # Extract the changes made by Trustcall and add the the ToolMessage returned to task_mAIstro
    todo_update_msg = extract_tool_info(spy.called_tools, tool_name)
    return {"messages": [{"role": "tool", "content": todo_update_msg, "tool_call_id": tool_call_id}]}

def update_instructions(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflect on the chat history and update the memory collection."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    
    namespace = ("instructions", todo_category, user_id)

    existing_memory = store.get(namespace, "user_instructions")
        
    # Format the memory in the system prompt
    system_msg = CREATE_INSTRUCTIONS.format(current_instructions=existing_memory.value if existing_memory else None)
    new_memory = model.invoke([SystemMessage(content=system_msg)]+state['messages'][:-1] + [HumanMessage(content="Please update the instructions based on the conversation")])

    # Overwrite the existing memory in the store 
    key = "user_instructions"
    store.put(namespace, key, {"memory": new_memory.content})
    tool_calls = state['messages'][-1].tool_calls
    tool_call_id = tool_calls[0].get('id')
    # Return tool message with update verification
    return {"messages": [{"role": "tool", "content": "updated instructions", "tool_call_id": tool_call_id}]}

# Conditional edge
def route_message(state: MessagesState, config: RunnableConfig, store: BaseStore) -> Literal[END, "update_todos", "update_instructions", "calendar_tools"]:

    """Reflect on the memories and chat history to decide whether to update the memory collection."""
    message = state['messages'][-1]
    if len(message.tool_calls) == 0:
        return END
    else:
        for tool_call in message.tool_calls:
            print("Tool calls: ", tool_call)
            # Only route UpdateMemory tool calls - other tool calls (like calendar) 
            # are handled directly within the task_mAIstro node
            
            # Access tool_call properties correctly (as a dictionary)
            tool_name = tool_call.get('name')
            print(f"Processing tool: {tool_name}")
            
            if tool_name == "UpdateMemory":
                update_type = tool_call['args'].get('update_type')
                if update_type == "todo":
                    return "update_todos"
                elif update_type == "instructions":
                    return "update_instructions"
            elif tool_name == "list_events" or tool_name in ["create_event", "update_event", "delete_event"]:
                print("TRANSITIONED TO CALENDAR TOOLS")
                return "calendar_tools"
            
            # Check if it's any other calendar tool by checking against calendar_tools list
            global calendar_tools
            if calendar_tools and any(getattr(tool, 'name', None) == tool_name for tool in calendar_tools):
                print(f"Routing calendar tool: {tool_name}")
                return "calendar_tools"
                
            return END

# Create the graph + all nodes
@asynccontextmanager
async def task_mAIstro_graph():
    async with MultiServerMCPClient(SERVER_CONFIGS) as client:
        global calendar_tools
        calendar_tools = client.get_tools()

        builder = StateGraph(MessagesState, config_schema=configuration.Configuration)

        # Define the flow of the memory extraction process
        builder.add_node(task_mAIstro)
        builder.add_node(update_todos)
        builder.add_node(update_instructions)
        builder.add_node("calendar_tools", ToolNode(calendar_tools))

        # Define the flow 
        builder.add_edge(START, "task_mAIstro")
        builder.add_conditional_edges("task_mAIstro", route_message)
        builder.add_edge("update_todos", "task_mAIstro")
        builder.add_edge("update_instructions", "task_mAIstro")
        builder.add_edge("calendar_tools", "task_mAIstro")

        # Compile the graph
        yield builder.compile()