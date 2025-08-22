#!/usr/bin/env python3
"""
Tunnel CLI - Command line tool for managing tunnels
"""
import os
import sys
import json
import argparse
import requests
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from getpass import getpass
from tabulate import tabulate

# Configuration
CONFIG_DIR = Path.home() / ".tunnel-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
API_BASE_URL = "https://api.tunnel.ovream.com/api/v1"


class TunnelCLI:
    def __init__(self):
        self.config = self.load_config()
        self.api_key = self.config.get("api_key")
        self.api_url = self.config.get("api_url", API_BASE_URL)
        self.user_info = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {}
    
    def save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        # Set restrictive permissions
        os.chmod(CONFIG_FILE, 0o600)
    
    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request with authentication"""
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        url = f"{self.api_url}{endpoint}"
        response = requests.request(method, url, headers=headers, **kwargs)
        
        if response.status_code == 401:
            print("Authentication failed. Please login again.")
            sys.exit(1)
        
        return response
    
    def login(self, username: Optional[str] = None):
        """Login and get API key"""
        if not username:
            username = input("Username: ")
        password = getpass("Password: ")
        
        # First login to get JWT token
        response = requests.post(
            f"{self.api_url}/auth/login",
            json={"username": username, "password": password}
        )
        
        if response.status_code != 200:
            print(f"Login failed: {response.json().get('detail', 'Unknown error')}")
            sys.exit(1)
        
        tokens = response.json()
        access_token = tokens["access_token"]
        
        # Get user profile to know their role
        profile_response = requests.get(
            f"{self.api_url}/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if profile_response.status_code == 200:
            user_data = profile_response.json()
            user_role = user_data.get("role", "user")
        else:
            user_role = "user"
        
        # Create API key
        response = requests.post(
            f"{self.api_url}/api-keys/",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"name": "CLI Key"}
        )
        
        if response.status_code != 200:
            print(f"Failed to create API key: {response.json().get('detail', 'Unknown error')}")
            sys.exit(1)
        
        api_key_data = response.json()
        api_key = api_key_data["key"]
        
        # Save configuration
        self.config["api_key"] = api_key
        self.config["api_url"] = self.api_url
        self.config["username"] = username
        self.config["user_role"] = user_role
        self.save_config(self.config)
        
        print(f"✓ Logged in as {username} ({user_role})")
        print(f"✓ API key saved to {CONFIG_FILE}")
        
        self.api_key = api_key
    
    def logout(self):
        """Clear saved credentials"""
        if CONFIG_FILE.exists():
            os.remove(CONFIG_FILE)
        print("✓ Logged out successfully")
    
    def list_tunnels(self):
        """List all tunnels"""
        response = self.request("GET", "/cli/tunnels")
        
        if response.status_code != 200:
            print(f"Failed to list tunnels: {response.json().get('detail', 'Unknown error')}")
            sys.exit(1)
        
        tunnels = response.json()
        
        if not tunnels:
            print("No tunnels found.")
            return
        
        # Format for display
        table_data = []
        for tunnel in tunnels:
            table_data.append([
                tunnel["subdomain"],
                tunnel["remote_port"],
                tunnel["status"],
                tunnel["url"]
            ])
        
        print(tabulate(
            table_data,
            headers=["Subdomain", "Port", "Status", "URL"],
            tablefmt="grid"
        ))
    
    def get_user_profile(self):
        """Get current user profile to check role"""
        if self.user_info:
            return self.user_info
            
        response = self.request("GET", "/users/me")
        if response.status_code == 200:
            self.user_info = response.json()
            return self.user_info
        return None
    
    def create_tunnel(self, subdomain: Optional[str] = None, local_port: int = 3000):
        """Create a new tunnel"""
        # Check subdomain length based on user role
        if subdomain:
            # Get user role from config or API
            user_role = self.config.get("user_role")
            if not user_role:
                profile = self.get_user_profile()
                user_role = profile.get("role", "user") if profile else "user"
                # Cache the role
                self.config["user_role"] = user_role
                self.save_config(self.config)
            
            # Validate subdomain length based on role
            min_length = 1 if user_role == "admin" else 5
            if len(subdomain) < min_length:
                print(f"Error: Subdomain must be at least {min_length} character{'s' if min_length > 1 else ''} long")
                if user_role != "admin":
                    print("Regular users must use subdomains with 5 or more characters")
                sys.exit(1)
            
            # Validate subdomain format
            import re
            if not re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', subdomain):
                print("Error: Invalid subdomain format. Use only lowercase letters, numbers, and hyphens")
                sys.exit(1)
        
        data = {"local_port": local_port}
        if subdomain:
            data["subdomain"] = subdomain
        
        response = self.request("POST", "/tunnels/", json=data)
        
        if response.status_code != 200:
            error = response.json()
            print(f"Failed to create tunnel: {error.get('detail', 'Unknown error')}")
            sys.exit(1)
        
        tunnel = response.json()
        print(f"✓ Tunnel created successfully!")
        print(f"  ID: {tunnel['id']}")
        print(f"  Subdomain: {tunnel['subdomain']}")
        print(f"  Port: {tunnel['remote_port']}")
        print(f"  URL: {tunnel['full_url']}")
        
        return tunnel
    
    def delete_tunnel(self, tunnel_id: str):
        """Delete a tunnel"""
        response = self.request("DELETE", f"/tunnels/{tunnel_id}")
        
        if response.status_code != 200:
            print(f"Failed to delete tunnel: {response.json().get('detail', 'Unknown error')}")
            sys.exit(1)
        
        print("✓ Tunnel deleted successfully")
    
    def connect_tunnel(self, tunnel_id: str, local_port: int):
        """Connect to a tunnel using FRP"""
        # Get tunnel configuration
        response = self.request(
            "GET",
            f"/cli/tunnels/{tunnel_id}/config",
            params={"local_port": local_port, "format": "ini"}
        )
        
        if response.status_code != 200:
            print(f"Failed to get tunnel config: {response.json().get('detail', 'Unknown error')}")
            sys.exit(1)
        
        config_data = response.json()
        config = config_data["config"]
        tunnel_info = config_data["tunnel"]
        
        print(f"Connecting to tunnel...")
        print(f"  Subdomain: {tunnel_info['subdomain']}")
        print(f"  Remote Port: {tunnel_info['remote_port']}")
        print(f"  Local Port: {local_port}")
        print(f"  URL: {tunnel_info['url']}")
        print()
        
        # Check if frpc is installed
        try:
            subprocess.run(["frpc", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: frpc is not installed.")
            print("Please install frpc from: https://github.com/fatedier/frp/releases")
            sys.exit(1)
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write(config)
            config_file = f.name
        
        try:
            # Mark tunnel as connected
            self.request("POST", f"/cli/tunnels/{tunnel_id}/connect", json={"local_port": local_port})
            
            print(f"Starting FRP client...")
            print(f"Press Ctrl+C to stop\n")
            
            # Run frpc
            process = subprocess.Popen(
                ["frpc", "-c", config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Stream output
            for line in process.stdout:
                print(line, end="")
            
            process.wait()
            
        except KeyboardInterrupt:
            print("\nStopping tunnel...")
            if process:
                process.terminate()
        finally:
            # Mark tunnel as disconnected
            self.request("POST", f"/cli/tunnels/{tunnel_id}/disconnect")
            # Clean up config file
            os.unlink(config_file)
            print("✓ Tunnel disconnected")
    
    def quick_tunnel(self, local_port: int = 3000):
        """Create and connect to a tunnel in one command"""
        # Create tunnel
        print("Creating tunnel...")
        tunnel = self.create_tunnel(local_port=local_port)
        
        # Connect to it
        print("\nConnecting to tunnel...")
        self.connect_tunnel(tunnel["id"], local_port)


def main():
    parser = argparse.ArgumentParser(description="Tunnel CLI - Manage tunnels from the command line")
    parser.add_argument("--api-url", help="API URL (default: https://api.tunnel.ovream.com/api/v1)")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Login command
    login_parser = subparsers.add_parser("login", help="Login to the tunnel service")
    login_parser.add_argument("username", nargs="?", help="Username")
    
    # Logout command
    subparsers.add_parser("logout", help="Logout and clear credentials")
    
    # List command
    subparsers.add_parser("list", help="List all tunnels")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new tunnel")
    create_parser.add_argument("--subdomain", help="Custom subdomain")
    create_parser.add_argument("--port", type=int, default=3000, help="Local port (default: 3000)")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a tunnel")
    delete_parser.add_argument("tunnel_id", help="Tunnel ID")
    
    # Connect command
    connect_parser = subparsers.add_parser("connect", help="Connect to a tunnel")
    connect_parser.add_argument("tunnel_id", help="Tunnel ID")
    connect_parser.add_argument("local_port", type=int, help="Local port to expose")
    
    # Quick command
    quick_parser = subparsers.add_parser("quick", help="Create and connect to a tunnel quickly")
    quick_parser.add_argument("port", type=int, nargs="?", default=3000, help="Local port to expose (default: 3000)")
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = TunnelCLI()
    
    if args.api_url:
        cli.api_url = args.api_url
    
    # Check if logged in for commands that require auth
    if args.command and args.command not in ["login", "logout"]:
        if not cli.api_key:
            print("Not logged in. Please run 'tunnel login' first.")
            sys.exit(1)
    
    # Execute command
    if args.command == "login":
        cli.login(args.username)
    elif args.command == "logout":
        cli.logout()
    elif args.command == "list":
        cli.list_tunnels()
    elif args.command == "create":
        cli.create_tunnel(args.subdomain, args.port)
    elif args.command == "delete":
        cli.delete_tunnel(args.tunnel_id)
    elif args.command == "connect":
        cli.connect_tunnel(args.tunnel_id, args.local_port)
    elif args.command == "quick":
        cli.quick_tunnel(args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()