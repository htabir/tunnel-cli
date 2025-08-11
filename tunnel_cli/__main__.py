#!/usr/bin/env python3
"""
Entry point for tunnel CLI
"""
import sys
import os


def main():
    """Main entry point for the tunnel command"""
    # Import here to avoid circular imports
    from .tunnel_tui import TunnelApp
    
    # Allow custom API URL via environment variable or argument
    if len(sys.argv) > 1:
        if sys.argv[1] == "--version":
            from . import __version__
            print(f"tunnel v{__version__}")
            sys.exit(0)
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Tunnel CLI - Terminal User Interface for managing tunnels")
            print("\nUsage:")
            print("  tunnel              Start the TUI")
            print("  tunnel --version    Show version")
            print("  tunnel --help       Show this help")
            print("\nEnvironment Variables:")
            print("  TUNNEL_API_URL      Custom API URL (default: https://api.tunnel.ovream.com/api/v1)")
            sys.exit(0)
        elif sys.argv[1].startswith("--api-url="):
            api_url = sys.argv[1].split("=", 1)[1]
            os.environ["TUNNEL_API_URL"] = api_url
    
    # Run the TUI app
    app = TunnelApp()
    app.run()


if __name__ == "__main__":
    main()