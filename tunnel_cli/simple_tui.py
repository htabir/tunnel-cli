#!/usr/bin/env python3
"""
Enhanced Tunnel CLI with better TUI layout
More descriptive and informative interface
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Center, Middle
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Input, Label, DataTable, Static, 
    LoadingIndicator, RichLog, Rule, Panel
)
from textual.message import Message
from rich.text import Text
from rich.panel import Panel as RichPanel

from .api_client import APIClient
from .config_manager import ConfigManager
from .auth_server import AuthServer


class LoginScreen(Screen):
    """Enhanced login screen with better layout"""
    
    CSS = """
    LoginScreen {
        align: center middle;
    }
    
    #login-panel {
        width: 70;
        height: auto;
        max-width: 100;
        padding: 1 2;
    }
    
    .help-text {
        color: $text-muted;
        margin: 1 0;
    }
    
    .option-title {
        color: $success;
        text-style: bold;
        margin: 1 0;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("b", "browser_auth", "Browser Auth", show=True),
        Binding("m", "manual_auth", "Manual Key", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Center():
            with Middle():
                with Vertical(id="login-panel"):
                    yield Static(
                        "[bold cyan]🚀 Tunnel CLI Authentication[/bold cyan]\n",
                        classes="title"
                    )
                    yield Rule()
                    
                    # Help text
                    yield Static(
                        "Welcome to Tunnel CLI! This tool helps you create secure\n"
                        "tunnels to expose your local services to the internet.\n"
                        "\n"
                        "First, you need to authenticate with your Tunnel account.",
                        classes="help-text"
                    )
                    
                    yield Rule(style="dim")
                    
                    # Option 1: Browser Auth
                    yield Static("\n[green]Option 1: Browser Authentication[/green] [dim](Recommended)[/dim]")
                    yield Static(
                        "  • Press [bold]B[/bold] to open your browser\n"
                        "  • Login to your Tunnel account\n" 
                        "  • An API key will be created automatically\n"
                        "  • The key will be sent back to this CLI\n"
                        "  • No copy-paste required!",
                        classes="help-text"
                    )
                    
                    # Option 2: Manual
                    yield Static("\n[yellow]Option 2: Manual API Key[/yellow]")
                    yield Static(
                        "  • Press [bold]M[/bold] to enter manual mode\n"
                        "  • Go to https://tunnel.ovream.com/api-keys\n"
                        "  • Create a new API key\n"
                        "  • Copy and paste it here",
                        classes="help-text"
                    )
                    
                    yield Rule(style="dim")
                    
                    # API Key input (hidden initially)
                    yield Label("\nAPI Key:", id="api-label", classes="hidden")
                    yield Input(
                        placeholder="Paste your API key here (tk_...)",
                        id="api-key",
                        password=True,
                        classes="hidden"
                    )
                    
                    # Action buttons
                    yield Static("")  # Spacer
                    with Horizontal(id="button-group"):
                        yield Button(
                            "🌐 Browser Auth [B]",
                            variant="success",
                            id="browser"
                        )
                        yield Button(
                            "🔑 Manual Key [M]",
                            variant="warning",
                            id="manual"
                        )
                        yield Button(
                            "❌ Quit [Q]",
                            variant="error",
                            id="quit"
                        )
        
        yield Footer()
    
    @on(Button.Pressed, "#browser")
    async def handle_browser_auth(self, event: Button.Pressed) -> None:
        """Start browser authentication flow"""
        import webbrowser
        
        # Create a rich log for status updates
        log_widget = RichLog(id="status-log", highlight=True, markup=True)
        container = self.query_one("#login-panel")
        container.mount(log_widget)
        
        log_widget.write("[yellow]Starting authentication server...[/yellow]")
        
        auth_server = AuthServer()
        try:
            await auth_server.start()
            auth_url = auth_server.get_auth_url()
            
            log_widget.write(f"[green]✓ Server started[/green]")
            log_widget.write(f"[cyan]Opening browser to:[/cyan] {auth_url}")
            
            webbrowser.open(auth_url)
            
            log_widget.write("[yellow]Waiting for authentication (2 minute timeout)...[/yellow]")
            log_widget.write("[dim]Please complete login in your browser[/dim]")
            
            api_key = await auth_server.wait_for_auth(timeout=120)
            
            if api_key:
                log_widget.write("[green]✓ API key received![/green]")
                await self.authenticate_with_key(api_key)
            else:
                log_widget.write("[red]✗ Authentication timeout[/red]")
                log_widget.write("[yellow]Please try manual authentication instead[/yellow]")
        
        except Exception as e:
            log_widget.write(f"[red]Error: {str(e)}[/red]")
        
        finally:
            await auth_server.stop()
    
    @on(Button.Pressed, "#manual")
    def handle_manual_auth(self, event: Button.Pressed) -> None:
        """Show manual API key input"""
        # Show the input fields
        self.query_one("#api-label").remove_class("hidden")
        self.query_one("#api-key").remove_class("hidden")
        self.query_one("#api-key").focus()
        
        # Add authenticate button
        if not self.query_one("#button-group").query("#authenticate"):
            auth_btn = Button(
                "✓ Authenticate [Enter]",
                variant="primary",
                id="authenticate"
            )
            self.query_one("#button-group").mount(auth_btn, before=2)
    
    @on(Button.Pressed, "#authenticate")
    async def handle_authenticate(self, event: Button.Pressed) -> None:
        """Authenticate with provided API key"""
        api_key = self.query_one("#api-key").value.strip()
        
        if not api_key:
            self.notify("Please enter an API key", severity="error")
            return
        
        if not api_key.startswith("tk_"):
            self.notify("Invalid API key format (should start with tk_)", severity="error")
            return
        
        await self.authenticate_with_key(api_key)
    
    async def authenticate_with_key(self, api_key: str) -> None:
        """Common authentication logic"""
        self.notify("Authenticating...", severity="information")
        
        try:
            await self.app.authenticate_with_key(api_key)
            self.app.push_screen("dashboard")
        except Exception as e:
            self.notify(f"Authentication failed: {str(e)}", severity="error")
    
    @on(Button.Pressed, "#quit")
    def handle_quit(self, event: Button.Pressed) -> None:
        """Quit the application"""
        self.app.exit()
    
    def action_browser_auth(self) -> None:
        """Keyboard shortcut for browser auth"""
        self.query_one("#browser").press()
    
    def action_manual_auth(self) -> None:
        """Keyboard shortcut for manual auth"""
        self.query_one("#manual").press()
    
    def action_quit(self) -> None:
        """Keyboard shortcut for quit"""
        self.app.exit()


class DashboardScreen(Screen):
    """Enhanced dashboard with better information display"""
    
    CSS = """
    DashboardScreen {
        layout: vertical;
    }
    
    #stats-panel {
        height: 8;
        margin: 1;
    }
    
    #tunnels-panel {
        margin: 1;
    }
    
    DataTable {
        height: 100%;
    }
    """
    
    BINDINGS = [
        Binding("n", "new_tunnel", "New Tunnel", show=True),
        Binding("d", "delete_tunnel", "Delete", show=True),
        Binding("c", "connect_tunnel", "Connect", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("l", "logout", "Logout", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical():
            # User info and stats
            with Panel(title="Dashboard", border_style="cyan", id="stats-panel"):
                yield Static(f"[bold]User:[/bold] {self.app.config.username}")
                yield Static(f"[bold]Server:[/bold] tunnel.ovream.com")
                yield Static(f"[bold]Status:[/bold] [green]Connected[/green]")
            
            # Tunnels table
            with Panel(title="Your Tunnels", border_style="green", id="tunnels-panel"):
                yield DataTable(id="tunnels-table", cursor_type="row")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Load tunnels when screen mounts"""
        await self.load_tunnels()
    
    async def load_tunnels(self) -> None:
        """Load and display tunnels"""
        table = self.query_one("#tunnels-table", DataTable)
        table.clear(columns=True)
        
        # Add columns
        table.add_columns(
            ("ID", 12),
            ("Subdomain", 20),
            ("Port", 8),
            ("Status", 10),
            ("URL", 40)
        )
        
        try:
            tunnels = await self.app.api_client.list_tunnels()
            
            if tunnels:
                for tunnel in tunnels:
                    status_color = "green" if tunnel.get("status") == "active" else "yellow"
                    table.add_row(
                        tunnel.get("id", "")[:8],
                        tunnel.get("subdomain", ""),
                        str(tunnel.get("remote_port", "")),
                        Text(tunnel.get("status", ""), style=status_color),
                        tunnel.get("url", "")
                    )
                
                self.notify(f"Loaded {len(tunnels)} tunnel(s)", severity="success")
            else:
                table.add_row(
                    "-",
                    "No tunnels yet",
                    "-",
                    "-",
                    "Press 'N' to create your first tunnel"
                )
        
        except Exception as e:
            self.notify(f"Failed to load tunnels: {str(e)}", severity="error")
            table.add_row("-", "Error loading", "-", "-", str(e)[:40])
    
    def action_new_tunnel(self) -> None:
        """Create new tunnel"""
        self.app.push_screen("create_tunnel")
    
    async def action_delete_tunnel(self) -> None:
        """Delete selected tunnel"""
        table = self.query_one("#tunnels-table", DataTable)
        if table.cursor_row is not None and table.cursor_row >= 0:
            row = table.get_row_at(table.cursor_row)
            if row and row[0] != "-":
                tunnel_id = row[0]
                try:
                    await self.app.api_client.delete_tunnel(tunnel_id)
                    self.notify("Tunnel deleted", severity="success")
                    await self.load_tunnels()
                except Exception as e:
                    self.notify(f"Failed to delete: {str(e)}", severity="error")
        else:
            self.notify("Please select a tunnel first", severity="warning")
    
    async def action_refresh(self) -> None:
        """Refresh tunnel list"""
        await self.load_tunnels()
    
    def action_logout(self) -> None:
        """Logout and return to login"""
        self.app.config.clear()
        self.app.push_screen("login")
    
    def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()


class CreateTunnelScreen(Screen):
    """Create tunnel screen with helpful information"""
    
    CSS = """
    CreateTunnelScreen {
        align: center middle;
    }
    
    #create-panel {
        width: 60;
        padding: 2;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "create", "Create", show=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Center():
            with Middle():
                with Panel(title="Create New Tunnel", border_style="cyan", id="create-panel"):
                    yield Static(
                        "[dim]Create a secure tunnel to expose your local service[/dim]\n"
                    )
                    
                    yield Label("Local Port:")
                    yield Input(
                        placeholder="e.g., 3000, 8080, 5000",
                        id="port",
                        value="3000"
                    )
                    yield Static(
                        "[dim]The port your local application is running on[/dim]\n"
                    )
                    
                    yield Label("Subdomain (optional):")
                    yield Input(
                        placeholder="e.g., my-app, test-server",
                        id="subdomain"
                    )
                    yield Static(
                        "[dim]Leave empty for a random subdomain\n"
                        "Your tunnel will be: [subdomain].tunnel.ovream.com[/dim]\n"
                    )
                    
                    with Horizontal():
                        yield Button("Create [Enter]", variant="primary", id="create")
                        yield Button("Cancel [Esc]", variant="default", id="cancel")
        
        yield Footer()
    
    @on(Button.Pressed, "#create")
    async def handle_create(self, event: Button.Pressed) -> None:
        """Create the tunnel"""
        port_str = self.query_one("#port").value
        subdomain = self.query_one("#subdomain").value.strip()
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")
        except ValueError as e:
            self.notify(str(e), severity="error")
            return
        
        self.notify("Creating tunnel...", severity="information")
        
        try:
            tunnel = await self.app.api_client.create_tunnel(
                local_port=port,
                subdomain=subdomain if subdomain else None
            )
            self.notify(
                f"Tunnel created: {tunnel['full_url']}",
                severity="success"
            )
            self.app.pop_screen()
        except Exception as e:
            self.notify(f"Failed to create tunnel: {str(e)}", severity="error")
    
    @on(Button.Pressed, "#cancel")
    def handle_cancel(self, event: Button.Pressed) -> None:
        """Cancel and go back"""
        self.app.pop_screen()
    
    def action_create(self) -> None:
        """Keyboard shortcut for create"""
        self.query_one("#create").press()
    
    def action_cancel(self) -> None:
        """Keyboard shortcut for cancel"""
        self.app.pop_screen()


class TunnelApp(App):
    """Enhanced Tunnel CLI Application"""
    
    CSS = """
    .hidden {
        display: none;
    }
    """
    
    TITLE = "Tunnel CLI"
    SUB_TITLE = "Secure Tunnel Management"
    
    SCREENS = {
        "login": LoginScreen,
        "dashboard": DashboardScreen,
        "create_tunnel": CreateTunnelScreen,
    }
    
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.api_client = APIClient()
    
    async def on_mount(self) -> None:
        """Initialize app on mount"""
        # Set API URL
        import os
        api_url = os.environ.get("TUNNEL_API_URL", self.config.api_url)
        self.api_client.api_url = api_url
        
        # Initialize API client session
        await self.api_client.__aenter__()
        
        # Check for saved credentials
        if self.config.api_key:
            self.api_client.set_api_key(self.config.api_key)
            try:
                await self.api_client.get_profile()
                self.push_screen("dashboard")
            except:
                self.config.clear()
                self.push_screen("login")
        else:
            self.push_screen("login")
    
    async def authenticate_with_key(self, api_key: str) -> None:
        """Authenticate with API key"""
        self.api_client.set_api_key(api_key)
        
        # Validate key
        profile = await self.api_client.get_profile()
        
        # Save credentials
        self.config.api_key = api_key
        self.config.username = profile.get("username", "User")
        
        self.notify(f"Welcome, {self.config.username}!", severity="success")
    
    async def on_shutdown(self) -> None:
        """Cleanup on shutdown"""
        await self.api_client.__aexit__(None, None, None)


def main():
    """Main entry point"""
    app = TunnelApp()
    app.run()


if __name__ == "__main__":
    main()