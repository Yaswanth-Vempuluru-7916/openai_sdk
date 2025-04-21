# pip install google-generativeai mcp python-dotenv
import asyncio
import os
import json
from datetime import datetime
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Validate required environment variables
required_env_vars = {
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "STAGE_DB_URL": os.getenv("STAGE_DB_URL"),
    "BASE_URL": os.getenv("BASE_URL"),
    "TOKEN": os.getenv("TOKEN"),
    "DB_PASSWORD" : os.getenv("DB_PASSWORD")
}

# print(required_env_vars["BASE_URL"])
# print(required_env_vars["TOKEN"])
missing_vars = [key for key, value in required_env_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}. Please set them in the .env file.")

# Initialize Gemini client
try:
    client = genai.Client(api_key=required_env_vars["GEMINI_API_KEY"])
except ValueError as e:
    raise ValueError(f"Failed to initialize Gemini client: {e}")

# MCP server configurations
mcp_servers = {
    # "stage-db": {
    #     "command": "node",
    #     "args": [
    #         "C:\\Users\\tejes\\Desktop\\Cat\\tasks\\stage-db\\dist\\index.js"
    #     ],
    #     "env": {
    #         "STAGE_DB_URL": required_env_vars["STAGE_DB_URL"]
    #     }
    # },
    # "staging-mcp": {
    #     "command": "node",
    #     "args": [
    #         "C:\\Users\\tejes\\Desktop\\Cat\\tasks\\mcp-staging\\dist\\index.js"
    #     ],
    #     "env": {
    #         "BASE_URL": required_env_vars["BASE_URL"],
    #         "TOKEN": required_env_vars["TOKEN"]
    #     }
    # }
     "mcp-garden": {
      "command": "node",
      "args": [
        "C:\\Users\\tejes\\Desktop\\Cat\\tasks\\mcp-garden\\dist\\index.js"
      ],
      "env": {
        "BASE_URL": required_env_vars["BASE_URL"],
        "TOKEN": required_env_vars["TOKEN"],
        "DB_NAME" : "stage_db",
        "DB_USER" : "yaswanth",
        "DB_PASSWORD" : "ya$wanth",
        "DB_HOST" : "162.55.81.185"
      }
    }
}

async def run():
    # Store tools from all servers
    all_tools = []
    
    # Process each MCP server
    for server_name, config in mcp_servers.items():
        print(f"Starting MCP server: {server_name}")
        server_params = StdioServerParameters(
            command=config["command"],
            args=config["args"],
            env=config["env"],
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # List available tools from the MCP server
                    mcp_tools = await session.list_tools()
                    if not mcp_tools.tools:
                        print(f"No tools available from {server_name}.")
                        continue

                    # Convert MCP tools to Gemini-compatible format
                    tools = [
                        types.Tool(
                            function_declarations=[
                                {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "parameters": {
                                        k: v
                                        for k, v in tool.inputSchema.items()
                                        if k not in ["additionalProperties", "$schema"]
                                    },
                                }
                            ]
                        )
                        for tool in mcp_tools.tools
                    ]
                    all_tools.extend(tools)

                    # Example prompt to test both servers
                    prompt = (
                        # "Run a SQL query to get the first 5 rows from the matched orders table "
                        # "fetch the latest 10 logs from the /stage-bit-ponder container."
                        "Whats happening with my transaction with initiator src address 7yTemZj69s9FgtBHp4dMxpW9kMSv7dXAwzvQNC7gqX7h"
                        "Using that unix timestamp fetch the logs of /staging-evm-relay"
                    )

                    # Generate content using Gemini API
                    response = client.models.generate_content(
                        model="gemini-2.5-pro-exp-03-25",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0,
                            tools=all_tools,
                        ),
                    )

                    # Handle function calls from the model
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if part.function_call:
                                function_call = part.function_call
                                print(f"Calling tool: {function_call.name}")

                                # Call the tool
                                result = await session.call_tool(
                                    function_call.name, arguments=dict(function_call.args)
                                )

                                # Parse and print formatted JSON result
                                print(f"--- Result from {function_call.name} ---")
                                try:
                                    result_data = json.loads(result.content[0].text)
                                    print(json.dumps(result_data, indent=2))
                                except json.JSONDecodeError:
                                    print("MCP server returned non-JSON response:")
                                    print(result.content[0].text)
                                except (IndexError, AttributeError):
                                    print("Unexpected result structure from MCP server:")
                                    print(result)
                    else:
                        print("No function call was generated by the model.")
                        if response.text:
                            print("Model response:")
                            print(response.text)
                        else:
                            print("No response text available.")
        except Exception as e:
            print(f"Error with {server_name}: {e}")

# Run the async function
if __name__ == "__main__":
    print("Starting MCP servers and querying...")
    asyncio.run(run())