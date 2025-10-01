# agent.py
import os
import asyncio
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from pathlib import Path
from uuid import uuid4

from utils import show_prompt, format_messages
from prompts import research_agent_prompt_with_mcp
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, AIMessage
from MCP_agent import agent_mcp, compress_research, begin_config  # import your compiled agent
from IPython.display import Image, display
from langgraph.checkpoint.memory import InMemorySaver
from research_scope import deep_researcher_builder

# Maximum recursion depth for agent
MAX_DEPTH = 50

dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

console = Console()


# Visualize user input flow
checkpointer = InMemorySaver()
scope = deep_researcher_builder.compile(checkpointer=checkpointer)
display(Image(scope.get_graph(xray=True).draw_mermaid_png()))

def filter_result(result):
    ai_messages = [msg for msg in result['messages'] if isinstance(msg, AIMessage)]

    # Get the last AI message content
    if ai_messages:
        last_ai_message = ai_messages[-1].content
        return last_ai_message
    
    return "Something went wrong."

async def send_message(purpose, repo_path):
     # Run the workflow
    thread = {"configurable": {"thread_id": str(uuid4())}}
    scope_result = scope.invoke(
        {"messages": [HumanMessage(content=purpose)]}, 
        config=thread
    )
    format_messages(scope_result['messages'])
    print(scope_result)

    if "research_brief" in scope_result:
        return await do_rest(repo_path, scope_result)
    
    return filter_result(scope_result)

async def send_clarification(clarification, repo_path):
    thread = {"configurable": {"thread_id": str(uuid4())}}
    clar_result = scope.invoke({"messages": [HumanMessage(content=clarification)]}, config=thread)
    format_messages(clar_result['messages'])
    
    show_prompt(research_agent_prompt_with_mcp, "Research Agent Instructions MCP")


    if "research_brief" in clar_result:
        return await do_rest(repo_path, clar_result)

    return filter_result(clar_result)


async def do_rest(repo_path, clar_result):
    # Get the absolute path to sample research docs
    # repo_path = os.path.abspath(repo_path)
    console.print(f"[bold blue]Sample docs path:[/bold blue] {repo_path}")

    if os.path.exists(repo_path):
        console.print(f"[green]✓ Directory exists with files:[/green] {os.listdir(repo_path)}")
    else:
        console.print("[red]✗ Directory does not exist![/red]")

    # MCP Client configuration
    mcp_config = {
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                repo_path
            ],
            "transport": "stdio"
        }
    }

    begin_config(repo_path)

    console.print(Panel("[bold yellow]Creating MCP client...[/bold yellow]", expand=False))
    client = MultiServerMCPClient(mcp_config)
    console.print("[green]✓ MCP client created successfully![/green]")
    # Get tools from MCP server
    console.print(Panel("[bold yellow]Getting tools...[/bold yellow]", expand=False))
    tools = await client.get_tools()

    # Display tools in a rich table
    table = Table(title="Available MCP Tools", show_header=True, header_style="bold magenta")
    table.add_column("Tool Name", style="cyan", width=25)
    table.add_column("Description", style="white", width=80)
    for tool in tools:
        description = tool.description[:77] + "..." if len(tool.description) > 80 else tool.description
        table.add_row(tool.name, description)
    console.print(table)
    console.print(f"[bold green]✓ Successfully retrieved {len(tools)} tools from MCP server[/bold green]")

    # Run the agent
    research_brief = clar_result["research_brief"]

    result = await agent_mcp.ainvoke(
        {"researcher_messages": [HumanMessage(content=f"{research_brief}.")]},
        config={"recursion_limit": MAX_DEPTH}
    )

    format_messages(result['researcher_messages'])

    # Compress research output if needed
    compressed = compress_research({"researcher_messages": result["researcher_messages"]})
    console.print(Markdown(compressed["compressed_research"]))
    return compressed["compressed_research"]

# --- Wrap async code in a main function ---
async def main():
    pass
    

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
