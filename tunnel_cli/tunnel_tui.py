#!/usr/bin/env python3
"""
Tunnel TUI - Terminal User Interface for managing tunnels
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Input, Label, DataTable, Static, LoadingIndicator, ListView, ListItem, RadioSet, RadioButton
from textual.message import Message

from .api_client import APIClient
from .config_manager import ConfigManager
from .auth_server import AuthServer


class LoginScreen(Screen):
    """Login screen for authentication"""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "submit", "Submit"),
        Binding("o", "open_browser", "Open Browser"),
        Binding("b", "browser_auth", "Browser Auth"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Static("🚀 Welcome to Tunnel CLI", classes="title"),
                Static("Authenticate with your API key", classes="subtitle"),
                Static(""),
                Static("🔐 Authentication Options:", classes="info"),
                Static(""),
                Static("Option 1: Automatic Browser Authentication (Recommended)"),
                Static("  • Press 'B' or click 'Browser Auth'"),
                Static("  • Login in your browser"),
                Static("  • The key will be received automatically"),
                Static(""),
                Static("Option 2: Manual API Key"),
                Static("  • Press 'O' to open the portal"),
                Static("  • Create an API key and paste it below"),
                Static(""),
                Label("API Key:"),
                Input(placeholder="Paste your API key here (tk_...)", id="api_key", password=True),
                Horizontal(
                    Button("Browser Auth", variant="success", id="browser_auth"),
                    Button("Open Portal", variant="default", id="open_browser"),
                    Button("Authenticate", variant="primary", id="authenticate"),
                    Button("Quit", variant="default", id="quit"),
                    classes="button-group"
                ),
                id="login-form",
                classes="form-container"
            ),
            id="login-container"
        )
        yield Footer()
    
    @on(Button.Pressed, "#browser_auth")
    async def handle_browser_auth(self, event: Button.Pressed) -> None:
        """Handle browser-based authentication with auto-receive"""
        import webbrowser
        
        self.app.notify("Starting authentication server...")
        
        # Start local auth server
        auth_server = AuthServer()
        try:
            await auth_server.start()
            
            # Get auth URL and open browser
            auth_url = auth_server.get_auth_url()
            self.app.notify(f"Opening browser for authentication...")
            webbrowser.open(auth_url)
            
            # Show waiting message
            self.app.notify("Waiting for authentication (2 minutes timeout)...")
            
            # Wait for API key
            api_key = await auth_server.wait_for_auth(timeout=120)
            
            if api_key:
                # Automatically fill the input and authenticate
                api_key_input = self.query_one("#api_key", Input)
                api_key_input.value = api_key
                self.app.notify("API key received! Authenticating...")
                await self.handle_authenticate(None)
            else:
                self.app.notify("Authentication timeout. Please paste your API key manually.", severity="warning")
        
        except Exception as e:
            self.app.notify(f"Browser auth failed: {str(e)}. Please use manual method.", severity="error")
        
        finally:
            await auth_server.stop()
    
    @on(Button.Pressed, "#open_browser")
    def handle_open_browser(self, event: Button.Pressed) -> None:
        """Open browser to get API key manually"""
        import webbrowser
        url = "https://tunnel.ovream.com/api-keys"
        self.app.notify(f"Opening {url}...")
        webbrowser.open(url)
    
    @on(Button.Pressed, "#authenticate")
    async def handle_authenticate(self, event: Button.Pressed) -> None:
        """Handle authenticate button press"""
        api_key = self.query_one("#api_key", Input).value.strip()
        
        if not api_key:
            self.app.notify("Please enter your API key", severity="error")
            return
        
        if not api_key.startswith("tk_"):
            self.app.notify("Invalid API key format. It should start with 'tk_'", severity="error")
            return
        
        # Show loading
        self.app.notify("Authenticating...")
        
        try:
            # Validate API key
            await self.app.authenticate_with_key(api_key)
            self.app.push_screen("dashboard")
        except Exception as e:
            self.app.notify(f"Authentication failed: {str(e)}", severity="error")
    
    @on(Button.Pressed, "#quit")
    def handle_quit(self, event: Button.Pressed) -> None:
        """Handle quit button"""
        self.app.exit()
    
    def action_open_browser(self) -> None:
        """Action to open browser"""
        self.handle_open_browser(None)
    
    async def action_browser_auth(self) -> None:
        """Action for browser authentication"""
        await self.handle_browser_auth(None)
    
    async def on_key(self, event) -> None:
        """Handle key presses"""
        if event.key == "enter":
            # Trigger authenticate when Enter is pressed
            api_key = self.query_one("#api_key", Input).value
            if api_key:
                await self.handle_authenticate(None)


class DashboardScreen(Screen):
    """Main dashboard showing tunnels"""
    
    BINDINGS = [
        Binding("n", "new_tunnel", "New Tunnel"),
        Binding("d", "delete_tunnel", "Delete"),
        Binding("c", "connect_tunnel", "Connect"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("l", "logout", "Logout"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Static(f"Tunnel Dashboard", classes="title"),
                Static(f"Logged in as: {self.app.config.username}", classes="subtitle"),
                DataTable(id="tunnels-table"),
                Horizontal(
                    Button("New Tunnel", variant="primary", id="new"),
                    Button("Connect", variant="success", id="connect"),
                    Button("Delete", variant="error", id="delete"),
                    Button("Refresh", variant="default", id="refresh"),
                    classes="button-group"
                ),
                id="dashboard-container"
            )
        )
        yield Footer()
    
    async def on_mount(self) -> None:
        """When screen is mounted, load tunnels"""
        await self.load_tunnels()
    
    async def load_tunnels(self) -> None:
        """Load and display tunnels"""
        table = self.query_one("#tunnels-table", DataTable)
        table.clear(columns=True)
        
        # Add columns
        table.add_columns("ID", "Subdomain", "Port", "Status", "URL")
        
        try:
            tunnels = await self.app.api_client.list_tunnels()
            
            if tunnels:
                for tunnel in tunnels:
                    table.add_row(
                        tunnel.get("id", "")[:8],
                        tunnel.get("subdomain", ""),
                        str(tunnel.get("remote_port", "")),
                        tunnel.get("status", ""),
                        tunnel.get("url", "")
                    )
            else:
                table.add_row("-", "No tunnels", "-", "-", "-")
                
        except Exception as e:
            self.app.notify(f"Failed to load tunnels: {str(e)}", severity="error")
            table.add_row("-", "Error loading", "-", "-", "-")
    
    @on(Button.Pressed, "#new")
    async def handle_new_tunnel(self, event: Button.Pressed) -> None:
        """Handle new tunnel button"""
        self.app.push_screen("create_tunnel")
    
    @on(Button.Pressed, "#connect")
    async def handle_connect(self, event: Button.Pressed) -> None:
        """Handle connect button"""
        table = self.query_one("#tunnels-table", DataTable)
        if table.cursor_row >= 0:
            row = table.get_row_at(table.cursor_row)
            if row and row[0] != "-":
                tunnel_id = row[0]
                self.app.selected_tunnel_id = tunnel_id
                self.app.push_screen("connect_tunnel")
        else:
            self.app.notify("Please select a tunnel", severity="warning")
    
    @on(Button.Pressed, "#delete")
    async def handle_delete(self, event: Button.Pressed) -> None:
        """Handle delete button"""
        table = self.query_one("#tunnels-table", DataTable)
        if table.cursor_row >= 0:
            row = table.get_row_at(table.cursor_row)
            if row and row[0] != "-":
                tunnel_id = row[0]
                try:
                    await self.app.api_client.delete_tunnel(tunnel_id)
                    self.app.notify("Tunnel deleted successfully", severity="success")
                    await self.load_tunnels()
                except Exception as e:
                    self.app.notify(f"Failed to delete tunnel: {str(e)}", severity="error")
        else:
            self.app.notify("Please select a tunnel", severity="warning")
    
    @on(Button.Pressed, "#refresh")
    async def handle_refresh(self, event: Button.Pressed) -> None:
        """Handle refresh button"""
        await self.load_tunnels()
        self.app.notify("Tunnels refreshed", severity="success")
    
    def action_new_tunnel(self) -> None:
        """Action for new tunnel"""
        self.app.push_screen("create_tunnel")
    
    async def action_delete_tunnel(self) -> None:
        """Action for delete tunnel"""
        await self.handle_delete(None)
    
    async def action_connect_tunnel(self) -> None:
        """Action for connect tunnel"""
        await self.handle_connect(None)
    
    async def action_refresh(self) -> None:
        """Action for refresh"""
        await self.load_tunnels()
    
    def action_logout(self) -> None:
        """Logout and return to login screen"""
        self.app.config.clear()
        self.app.push_screen("login")
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()


class CreateTunnelScreen(Screen):
    """Screen for creating a new tunnel"""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "submit", "Create"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Static("Create New Tunnel", classes="title"),
                Label("Local Port:"),
                Input(placeholder="3000", id="local_port", value="3000"),
                Label("Subdomain (optional):"),
                Input(placeholder="Leave empty for random", id="subdomain"),
                RadioSet(
                    RadioButton("Random subdomain", id="random", value=True),
                    RadioButton("Custom subdomain", id="custom"),
                    id="subdomain_type"
                ),
                Horizontal(
                    Button("Create", variant="primary", id="create"),
                    Button("Cancel", variant="default", id="cancel"),
                    classes="button-group"
                ),
                id="create-form",
                classes="form-container"
            ),
            id="create-container"
        )
        yield Footer()
    
    @on(RadioButton.Changed)
    def handle_radio_change(self, event: RadioButton.Changed) -> None:
        """Handle radio button change"""
        subdomain_input = self.query_one("#subdomain", Input)
        if event.radio_button.id == "random":
            subdomain_input.disabled = True
            subdomain_input.value = ""
        else:
            subdomain_input.disabled = False
    
    @on(Button.Pressed, "#create")
    async def handle_create(self, event: Button.Pressed) -> None:
        """Handle create button"""
        local_port = self.query_one("#local_port", Input).value
        subdomain = self.query_one("#subdomain", Input).value
        use_custom = self.query_one("#custom", RadioButton).value
        
        if not local_port:
            self.app.notify("Please enter a local port", severity="error")
            return
        
        try:
            port = int(local_port)
        except ValueError:
            self.app.notify("Invalid port number", severity="error")
            return
        
        if use_custom and not subdomain:
            self.app.notify("Please enter a subdomain or select random", severity="error")
            return
        
        self.app.notify("Creating tunnel...")
        
        try:
            tunnel = await self.app.api_client.create_tunnel(
                local_port=port,
                subdomain=subdomain if use_custom else None
            )
            self.app.notify(f"Tunnel created: {tunnel['full_url']}", severity="success")
            self.app.pop_screen()
        except Exception as e:
            self.app.notify(f"Failed to create tunnel: {str(e)}", severity="error")
    
    @on(Button.Pressed, "#cancel")
    def handle_cancel(self, event: Button.Pressed) -> None:
        """Handle cancel button"""
        self.app.pop_screen()


class ConnectTunnelScreen(Screen):
    """Screen for connecting to a tunnel"""
    
    BINDINGS = [
        Binding("escape", "disconnect", "Disconnect"),
        Binding("q", "disconnect", "Disconnect"),
    ]
    
    def __init__(self, tunnel_id: str):
        super().__init__()
        self.tunnel_id = tunnel_id
        self.connected = False
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Static("Connect to Tunnel", classes="title"),
                Label("Local Port:"),
                Input(placeholder="3000", id="local_port", value="3000"),
                Button("Connect", variant="primary", id="connect"),
                Container(id="connection-info"),
                ScrollableContainer(
                    Static("Waiting for connection...", id="logs"),
                    id="log-container"
                ),
                Button("Disconnect", variant="error", id="disconnect"),
                id="connect-form",
                classes="form-container"
            ),
            id="connect-container"
        )
        yield Footer()
    
    @on(Button.Pressed, "#connect")
    async def handle_connect(self, event: Button.Pressed) -> None:
        """Handle connect button"""
        local_port = self.query_one("#local_port", Input).value
        
        if not local_port:
            self.app.notify("Please enter a local port", severity="error")
            return
        
        try:
            port = int(local_port)
        except ValueError:
            self.app.notify("Invalid port number", severity="error")
            return
        
        self.app.notify("Connecting to tunnel...")
        
        try:
            # Get tunnel config
            config_data = await self.app.api_client.get_tunnel_config(self.tunnel_id, port)
            tunnel_info = config_data["tunnel"]
            
            # Update connection info
            info_container = self.query_one("#connection-info", Container)
            info_container.mount(
                Static(f"✓ Connected to: {tunnel_info['url']}", classes="success-message")
            )
            info_container.mount(
                Static(f"Local Port: {port} → Remote Port: {tunnel_info['remote_port']}")
            )
            
            # Mark as connected
            await self.app.api_client.connect_tunnel(self.tunnel_id, port)
            self.connected = True
            
            # Update logs
            logs = self.query_one("#logs", Static)
            logs.update(f"Tunnel connected successfully!\nURL: {tunnel_info['url']}\n\nWaiting for requests...")
            
            self.app.notify(f"Connected to {tunnel_info['url']}", severity="success")
            
        except Exception as e:
            self.app.notify(f"Failed to connect: {str(e)}", severity="error")
    
    @on(Button.Pressed, "#disconnect")
    async def handle_disconnect(self, event: Button.Pressed) -> None:
        """Handle disconnect button"""
        if self.connected:
            try:
                await self.app.api_client.disconnect_tunnel(self.tunnel_id)
                self.app.notify("Disconnected from tunnel", severity="success")
            except:
                pass
        self.app.pop_screen()
    
    async def action_disconnect(self) -> None:
        """Action for disconnect"""
        await self.handle_disconnect(None)


class TunnelApp(App):
    """Main TUI Application"""
    
    CSS = """
    #login-container, #dashboard-container, #create-container, #connect-container {
        align: center middle;
    }
    
    .form-container {
        width: 60;
        height: auto;
        border: solid #555;
        padding: 1 2;
        background: $surface;
    }
    
    .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }
    
    .subtitle {
        text-align: center;
        color: $text-muted;
        margin: 0 0 1 0;
    }
    
    .button-group {
        margin: 1 0;
        align: center middle;
        height: 3;
    }
    
    .button-group Button {
        margin: 0 1;
    }
    
    Input {
        margin: 0 0 1 0;
    }
    
    Label {
        margin: 0 0 0 0;
    }
    
    #tunnels-table {
        margin: 1 0;
        height: 15;
    }
    
    #log-container {
        height: 10;
        border: solid #555;
        margin: 1 0;
    }
    
    .success-message {
        color: $success;
        margin: 1 0;
    }
    
    RadioSet {
        margin: 1 0;
    }
    """
    
    TITLE = "Tunnel CLI"
    SCREENS = {
        "login": LoginScreen,
        "dashboard": DashboardScreen,
        "create_tunnel": CreateTunnelScreen,
    }
    
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.api_client = APIClient()
        self.selected_tunnel_id = None
    
    async def on_mount(self) -> None:
        """When app starts, check for existing credentials"""
        # Override API URL if set
        import os
        api_url = os.environ.get("TUNNEL_API_URL", self.config.api_url)
        self.api_client.api_url = api_url
        
        # Initialize API client session
        await self.api_client.__aenter__()
        
        # Check for saved API key
        if self.config.api_key:
            self.api_client.set_api_key(self.config.api_key)
            try:
                # Verify API key is still valid
                await self.api_client.get_profile()
                self.push_screen("dashboard")
            except:
                # API key invalid, clear it
                self.config.clear()
                self.push_screen("login")
        else:
            self.push_screen("login")
    
    async def authenticate_with_key(self, api_key: str) -> None:
        """Authenticate with API key"""
        # Set the API key
        self.api_client.set_api_key(api_key)
        
        # Validate the key by getting profile
        profile = await self.api_client.get_profile()
        
        # Save credentials
        self.config.api_key = api_key
        self.config.username = profile.get("username", "User")
        
        self.notify(f"Welcome back, {self.config.username}!", severity="success")
    
    def on_screen(self, event) -> None:
        """Handle screen changes"""
        if event.screen.name == "connect_tunnel" and self.selected_tunnel_id:
            # Replace with ConnectTunnelScreen with the selected tunnel
            self.pop_screen()
            self.push_screen(ConnectTunnelScreen(self.selected_tunnel_id))
    
    async def on_shutdown(self) -> None:
        """Clean up when app shuts down"""
        await self.api_client.__aexit__(None, None, None)


def main():
    """Main entry point"""
    import sys
    import os
    
    # Allow custom API URL via environment variable
    if len(sys.argv) > 1 and sys.argv[1].startswith("--api-url="):
        api_url = sys.argv[1].split("=", 1)[1]
        os.environ["TUNNEL_API_URL"] = api_url
    
    app = TunnelApp()
    app.run()


if __name__ == "__main__":
    main()