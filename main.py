# main.py
# Entry point for running the MCP server with stdio transport
# from mcp import FastMCP
from mcp.server.fastmcp import FastMCP
from utils.transaction_utils import transaction_status

def main():
    # Initialize MCP server
    mcp = FastMCP("Transaction Status Server")
    
    # Register the transaction status tool
    @mcp.tool()
    def check_transaction_status(initiator_source_address: str) -> str:
        """Check the status of a transaction by initiator source address."""
        return transaction_status(initiator_source_address)
    
    # Run the server with stdio transport
    print("Starting MCP server with stdio transport...")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()