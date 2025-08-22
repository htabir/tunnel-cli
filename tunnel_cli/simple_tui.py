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
    LoadingIndicator, RichLog
)
from textual.events import Key
from textual.message import Message
from rich.text import Text
# Panel is not used anymore

from .api_client import APIClient
from .config_manager import ConfigManager
from .auth_server import AuthServer
from .frp_client import FRPClientManager


class LoginScreen(Screen):
    """Enhanced login screen with better layout"""
    
    CSS = """
    LoginScreen {
        align: center middle;
    }
    
    #login-panel {
        width: 70;
        height: auto;
        max-height: 24;
        max-width: 100;
        padding: 1 2;
        border: solid $primary;
    }
    
    .title {
        text-align: center;
        margin: 0 0 0 0;
    }
    
    .subtitle {
        text-align: center;
        color: $text-muted;
        margin: 0 0 1 0;
    }
    
    .help-text {
        color: $text-muted;
        margin: 0 0 0 0;
        padding-left: 2;
    }
    
    .hidden {
        display: none;
    }
    
    #button-group {
        height: 3;
        width: 100%;
        margin: 1 0 0 0;
    }
    
    Button {
        margin: 0 1;
        min-width: 14;
    }
    
    Input {
        width: 100%;
        margin: 0 0 1 0;
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
                        "[bold cyan]🚀 Tunnel CLI Authentication[/bold cyan]",
                        classes="title"
                    )
                    yield Static("─" * 50)
                    
                    yield Static(
                        "Authenticate to create secure tunnels",
                        classes="subtitle"
                    )
                    
                    # Option 1: Browser Auth (ultra-compact)
                    yield Static("[green]◉ Browser Auth[/green] [dim](Recommended)[/dim] - Press [bold]B[/bold]")
                    yield Static(
                        "  Opens browser → Login → Auto-receives key",
                        classes="help-text"
                    )
                    
                    # Option 2: Manual (ultra-compact)
                    yield Static("[yellow]◉ Manual Key[/yellow] - Press [bold]M[/bold]")
                    yield Static(
                        "  Get key from tunnel.ovream.com/api-keys",
                        classes="help-text"
                    )
                    
                    yield Static("")  # Small spacer
                    
                    # API Key input (hidden initially)
                    yield Label("API Key:", id="api-label", classes="hidden")
                    yield Input(
                        id="api-key",
                        password=True,
                        classes="hidden"
                    )
                    
                    # Authenticate button (hidden initially)
                    yield Button(
                        "✓ Authenticate",
                        variant="primary",
                        id="authenticate",
                        classes="hidden"
                    )
                    
                    # Action buttons
                    with Horizontal(id="button-group"):
                        yield Button(
                            "🌐 Browser Auth",
                            variant="success",
                            id="browser"
                        )
                        yield Button(
                            "🔑 Manual Key",
                            variant="warning",
                            id="manual"
                        )
                        yield Button(
                            "❌ Quit",
                            variant="error",
                            id="quit"
                        )
        
        yield Footer()
    
    @on(Button.Pressed, "#browser")
    async def handle_browser_auth(self, event: Button.Pressed = None) -> None:
        """Start browser authentication flow"""
        import webbrowser
        
        self.notify("Starting browser authentication...", severity="information", timeout=2)
        
        auth_server = AuthServer()
        try:
            await auth_server.start()
            auth_url = auth_server.get_auth_url()
            
            self.notify(f"Opening browser...", timeout=2)
            webbrowser.open(auth_url)
            
            self.notify("Waiting for authentication (2 minute timeout)...", timeout=3)
            
            api_key = await auth_server.wait_for_auth(timeout=120)
            
            if api_key:
                self.notify("API key received!", severity="success", timeout=2)
                await self.authenticate_with_key(api_key)
            else:
                self.notify("Authentication timeout. Please try manual method.", severity="warning", timeout=3)
        
        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error", timeout=3)
        
        finally:
            await auth_server.stop()
    
    @on(Button.Pressed, "#manual")
    def handle_manual_auth(self, event: Button.Pressed = None) -> None:
        """Show manual API key input"""
        # Show the input fields
        api_label = self.query_one("#api-label", Label)
        api_input = self.query_one("#api-key", Input)
        
        # Remove hidden class if they have it
        if "hidden" in api_label.classes:
            api_label.remove_class("hidden")
        if "hidden" in api_input.classes:
            api_input.remove_class("hidden")
        
        # Focus the input
        api_input.focus()
        
        # Add authenticate button if not already there
        button_group = self.query_one("#button-group")
        if not button_group.query("#authenticate"):
            auth_btn = Button(
                "✓ Authenticate [Enter]",
                variant="primary",
                id="authenticate"
            )
            # Mount before the quit button (last one)
            buttons = list(button_group.query(Button))
            if buttons:
                button_group.mount(auth_btn, before=buttons[-1])
    
    @on(Button.Pressed, "#authenticate")
    async def handle_authenticate(self, event: Button.Pressed = None) -> None:
        """Authenticate with provided API key"""
        api_key = self.query_one("#api-key").value.strip()
        
        if not api_key:
            self.notify("Please enter an API key", severity="error", timeout=2)
            return
        
        if not api_key.startswith("tk_"):
            self.notify("Invalid API key format (should start with tk_)", severity="error", timeout=2)
            return
        
        await self.authenticate_with_key(api_key)
    
    async def authenticate_with_key(self, api_key: str) -> None:
        """Common authentication logic"""
        self.notify("Authenticating...", severity="information", timeout=2)
        
        try:
            await self.app.authenticate_with_key(api_key)
            self.app.push_screen("dashboard")
        except Exception as e:
            self.notify(f"Authentication failed: {str(e)}", severity="error", timeout=3)
    
    @on(Button.Pressed, "#quit")
    def handle_quit(self, event: Button.Pressed = None) -> None:
        """Quit the application"""
        self.app.exit()
    
    async def action_browser_auth(self) -> None:
        """Keyboard shortcut for browser auth"""
        await self.handle_browser_auth(None)
    
    def action_manual_auth(self) -> None:
        """Keyboard shortcut for manual auth"""
        self.handle_manual_auth(None)
    
    def action_quit(self) -> None:
        """Keyboard shortcut for quit"""
        self.app.exit()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input field"""
        if event.input.id == "api-key":
            await self.handle_authenticate(None)


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
        Binding("e", "edit_tunnel", "Edit Port", show=True),
        Binding("d", "delete_tunnel", "Delete", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("l", "logout", "Logout", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]
    
    def show_message(self, message: str, severity: str = "information"):
        """Show a simple status message instead of large notification"""
        # Update the footer or a status label instead of using notify
        # For now, we'll use notify with timeout=2 to make it disappear quickly
        self.notify(message, severity=severity, timeout=2)
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical():
            # User info and stats
            with Container(id="stats-panel"):
                yield Static("[bold cyan]═══ Dashboard ═══[/bold cyan]")
                yield Static(f"[bold]User:[/bold] {self.app.config.username}")
                yield Static(f"[bold]Server:[/bold] tunnel.ovream.com")
                yield Static(f"[bold]Status:[/bold] [green]Connected[/green]")
                yield Static("", id="quota-info")
                yield Static("─" * 50, classes="dim")
            
            # Tunnels table
            with Container(id="tunnels-panel"):
                yield Static("[bold green]═══ Your Tunnels ═══[/bold green]")
                yield DataTable(id="tunnels-table", cursor_type="row")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Load tunnels when screen mounts"""
        await self.load_quota_info()
        await self.load_tunnels()
        # Auto-connect tunnels with local ports
        await self.auto_connect_tunnels()
        # Start periodic status sync
        self.set_interval(30, self.periodic_sync)  # Sync every 30 seconds
    
    async def load_quota_info(self) -> None:
        """Load and display quota information"""
        try:
            quota = await self.app.api_client.get_quota_info()
            quota_text = self.query_one("#quota-info", Static)
            
            # Format tunnel quota
            max_tunnels = quota.get('max_tunnels', 0)
            used_tunnels = quota.get('used_tunnels', 0)
            if max_tunnels == -1:
                tunnels_info = f"[bold]Tunnels:[/bold] {used_tunnels}/∞"
            else:
                tunnels_info = f"[bold]Tunnels:[/bold] {used_tunnels}/{max_tunnels}"
            
            # Format custom domain quota
            max_custom = quota.get('max_custom_domains', 0)
            used_custom = quota.get('used_custom_domains', 0)
            if max_custom == -1:
                domains_info = f"[bold]Custom Domains:[/bold] {used_custom}/∞"
            else:
                domains_info = f"[bold]Custom Domains:[/bold] {used_custom}/{max_custom}"
            
            quota_text.update(f"[yellow]📊 Quota:[/yellow] {tunnels_info} | {domains_info}")
        except Exception as e:
            # If quota fails, just don't show it
            pass
    
    async def periodic_sync(self) -> None:
        """Periodic sync of connection status"""
        await self.sync_connection_status()
    
    async def load_tunnels(self) -> None:
        """Load and display tunnels"""
        table = self.query_one("#tunnels-table", DataTable)
        table.clear(columns=True)
        
        # Add columns
        table.add_columns("ID", "Subdomain", "Local", "Remote", "Status", "URL")
        
        # Store full tunnel data for later use
        self.tunnel_data = {}
        
        try:
            tunnels = await self.app.api_client.list_tunnels()
            
            if tunnels:
                for tunnel in tunnels:
                    tunnel_id = tunnel.get("id", "")
                    short_id = tunnel_id[:8]
                    # Store full tunnel data indexed by short ID
                    self.tunnel_data[short_id] = tunnel
                    
                    # Determine status based on local port and connection
                    local_port = tunnel.get("local_port")
                    local_port_str = str(local_port) if local_port else "-"
                    
                    # Check connection status
                    connection_status = self.app.frp_client_manager.get_tunnel_status(tunnel_id)
                    
                    if connection_status == "connected":
                        status_text = Text("● Connected", style="green")
                    elif local_port:
                        # Has local port but not connected - check if port is available
                        if await self._is_port_available(local_port):
                            status_text = Text("○ Ready", style="yellow")
                        else:
                            status_text = Text("○ Port down", style="red")
                    else:
                        status_text = Text("○ Manual", style="dim")
                    
                    # Add domain type indicator
                    is_custom = tunnel.get("is_custom_subdomain", False)
                    domain_type = "[C]" if is_custom else "[R]"
                    subdomain_with_type = f"{domain_type} {tunnel.get('subdomain', '')}"
                    
                    table.add_row(
                        short_id,
                        subdomain_with_type,
                        local_port_str,
                        str(tunnel.get("remote_port", "")),
                        status_text,
                        tunnel.get("url", "")
                    )
                
                # Don't show the "Loaded X tunnels" message - it's not needed
            else:
                table.add_row(
                    "-",
                    "No tunnels yet",
                    "-",
                    "-",
                    "-",
                    "Press 'N' to create"
                )
        
        except Exception as e:
            self.notify(f"Failed to load tunnels: {str(e)}", severity="error", timeout=3)
            table.add_row("-", "Error loading", "-", "-", "-", str(e)[:40])
    
    def action_new_tunnel(self) -> None:
        """Create new tunnel"""
        self.app.push_screen("create_tunnel")
    
    async def action_delete_tunnel(self) -> None:
        """Delete selected tunnel"""
        table = self.query_one("#tunnels-table", DataTable)
        if table.cursor_row is not None and table.cursor_row >= 0:
            row = table.get_row_at(table.cursor_row)
            if row and row[0] != "-":
                short_id = row[0]
                # Get the full tunnel data using the short ID
                tunnel_data = getattr(self, 'tunnel_data', {}).get(short_id)
                if tunnel_data:
                    full_tunnel_id = tunnel_data.get("id")
                    try:
                        await self.app.api_client.delete_tunnel(full_tunnel_id)
                        self.notify("Tunnel deleted", severity="success", timeout=2)
                        # Refresh the tunnels list immediately
                        await self.load_tunnels()
                    except Exception as e:
                        self.notify(f"Failed to delete: {str(e)}", severity="error", timeout=3)
                else:
                    self.notify("Tunnel data not found", severity="error", timeout=2)
        else:
            self.notify("Please select a tunnel first", severity="warning", timeout=2)
    
    async def action_edit_tunnel(self) -> None:
        """Edit local port for selected tunnel"""
        table = self.query_one("#tunnels-table", DataTable)
        if table.cursor_row is not None and table.cursor_row >= 0:
            row = table.get_row_at(table.cursor_row)
            if row and row[0] != "-":
                short_id = row[0]
                tunnel_data = getattr(self, 'tunnel_data', {}).get(short_id)
                if tunnel_data:
                    self.app.push_screen(EditTunnelPortScreen(tunnel_data))
                else:
                    self.notify("Tunnel data not found", severity="error", timeout=2)
        else:
            self.notify("Please select a tunnel first", severity="warning", timeout=2)
    
    async def _is_port_available(self, port: int) -> bool:
        """Check if a local port is listening"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0  # Port is open if connect succeeds
        finally:
            sock.close()
    
    async def auto_connect_tunnels(self) -> None:
        """Auto-connect tunnels that have local ports configured"""
        if not hasattr(self, 'tunnel_data'):
            return
            
        # Ensure FRP client is installed
        try:
            if not await self.app.frp_client_manager.ensure_frpc_installed():
                return
        except:
            return
        
        for short_id, tunnel in self.tunnel_data.items():
            local_port = tunnel.get("local_port")
            tunnel_id = tunnel.get("id")
            
            if local_port:
                # Check port availability and connection status
                port_available = await self._is_port_available(local_port)
                current_status = self.app.frp_client_manager.get_tunnel_status(tunnel_id)
                
                if port_available and current_status != "connected":
                    # Port is available but not connected - connect it
                    try:
                        await self.app.frp_client_manager.start_tunnel(tunnel, local_port)
                        # Report connected status
                        await self.app.api_client.update_connection_status(tunnel_id, "connected")
                    except:
                        pass  # Silently fail auto-connect
                elif not port_available and current_status == "connected":
                    # Port is down but we think we're connected - disconnect
                    try:
                        await self.app.frp_client_manager.stop_tunnel(tunnel_id)
                        # Report port_down status
                        await self.app.api_client.update_connection_status(tunnel_id, "port_down")
                    except:
                        pass
                elif not port_available:
                    # Port is down - report it
                    try:
                        await self.app.api_client.update_connection_status(tunnel_id, "port_down")
                    except:
                        pass
        
        # Refresh display to show connected status
        await self.load_tunnels()
    
    async def action_refresh(self) -> None:
        """Refresh tunnel list and quota"""
        await self.load_quota_info()
        await self.load_tunnels()
        await self.auto_connect_tunnels()
        await self.sync_connection_status()
    
    async def sync_connection_status(self) -> None:
        """Sync connection status with backend"""
        if not hasattr(self, 'tunnel_data'):
            return
        
        for short_id, tunnel in self.tunnel_data.items():
            tunnel_id = tunnel.get("id")
            local_port = tunnel.get("local_port")
            
            if local_port:
                # Check actual status
                frp_status = self.app.frp_client_manager.get_tunnel_status(tunnel_id)
                port_available = await self._is_port_available(local_port)
                
                # Determine real status
                if frp_status == "connected" and port_available:
                    status = "connected"
                elif not port_available:
                    status = "port_down"
                else:
                    status = "disconnected"
                
                # Report to backend
                try:
                    await self.app.api_client.update_connection_status(tunnel_id, status)
                except:
                    pass  # Silently fail status updates
    
    def action_logout(self) -> None:
        """Logout and return to login"""
        self.app.config.clear()
        self.app.push_screen("login")
    
    def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()


# ConnectTunnelScreen removed - auto-connect handles connection now


class CreateTunnelScreen(Screen):
    """Create tunnel screen with helpful information"""
    
    CSS = """
    CreateTunnelScreen {
        align: center middle;
    }
    
    #create-panel {
        width: 60;
        min-height: 20;
        max-height: 90%;
        padding: 1 2;
        border: solid $primary;
        overflow-y: auto;
    }
    
    #button-row {
        height: 3;
        width: 100%;
        margin-top: 1;
    }
    
    #button-row Button {
        width: 16;
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "create", "Create", show=False),
        Binding("p", "palette", "Palette", show=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Center():
            with Middle():
                with Container(id="create-panel"):
                    yield Static("[bold cyan]═══ Create New Tunnel ═══[/bold cyan]")
                    yield Static("")
                    yield Static(
                        "[dim]Create a secure tunnel to expose your local service[/dim]"
                    )
                    yield Static("")
                    
                    yield Label("Local Port:")
                    yield Input(
                        id="port"
                    )
                    yield Static(
                        "[dim]The port your local application is running on[/dim]"
                    )
                    yield Static("")
                    
                    yield Label("Subdomain (optional):", id="subdomain-label")
                    yield Input(
                        id="subdomain"
                    )
                    yield Static(
                        "[dim]Leave empty for a random subdomain[/dim]",
                        id="subdomain-help"
                    )
                    yield Static("", id="quota-warning")
                    yield Static(
                        "[blue]<random>.tunnel.ovream.com[/blue]",
                        id="tunnel-url"
                    )
                    yield Static("")
                    
                    # Instructions
                    yield Static("[bold green]Press ENTER to Create Tunnel[/bold green]  |  [bold red]Press ESC to Cancel[/bold red]", id="button-info")
                    yield Static("")
                    
                    # Buttons in horizontal container
                    with Horizontal(id="button-row"):
                        yield Button("Create Tunnel", variant="primary", id="create")
                        yield Button("Cancel", variant="default", id="cancel")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Setup event handlers when screen mounts and check quota"""
        subdomain_input = self.query_one("#subdomain", Input)
        subdomain_label = self.query_one("#subdomain-label", Label)
        subdomain_help = self.query_one("#subdomain-help", Static)
        quota_warning = self.query_one("#quota-warning", Static)
        
        subdomain_input.on_change = self.update_tunnel_url
        
        # Check quota for custom domains
        try:
            quota = await self.app.api_client.get_quota_info()
            can_use_custom = quota.get('can_use_custom_domain', True)
            
            if not can_use_custom:
                # Hide the subdomain input completely
                subdomain_label.display = False
                subdomain_input.display = False
                subdomain_help.display = False
                
                # Show warning that only random domains are available
                used = quota.get('used_custom_domains', 0)
                limit = quota.get('max_custom_domains', 0)
                quota_warning.update(
                    f"[bold yellow]⚠️ Custom domain quota exhausted ({used}/{limit})[/bold yellow]\n"
                    f"[dim]A random subdomain will be assigned automatically[/dim]"
                )
                
                # Update the URL display to show random will be assigned
                url_display = self.query_one("#tunnel-url", Static)
                url_display.update("[blue]<random>.tunnel.ovream.com[/blue]")
        except Exception as e:
            # Silent fail if quota endpoint not available
            pass
    
    def update_tunnel_url(self) -> None:
        """Update the tunnel URL display based on subdomain input"""
        subdomain_input = self.query_one("#subdomain", Input)
        url_display = self.query_one("#tunnel-url", Static)
        
        subdomain = subdomain_input.value.strip()
        if subdomain:
            url_display.update(f"[blue]{subdomain}.tunnel.ovream.com[/blue]")
        else:
            url_display.update("[blue]<random>.tunnel.ovream.com[/blue]")
    
    @on(Input.Changed, "#subdomain")
    def on_subdomain_changed(self, event: Input.Changed) -> None:
        """Handle subdomain input changes"""
        self.update_tunnel_url()
    
    @on(Button.Pressed, "#create")
    async def handle_create(self, event: Button.Pressed = None) -> None:
        """Create the tunnel"""
        port_str = self.query_one("#port").value
        subdomain = self.query_one("#subdomain").value.strip()
        
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")
        except ValueError as e:
            self.notify(str(e), severity="error", timeout=2)
            return
        
        self.notify("Creating tunnel...", severity="information", timeout=2)
        
        try:
            tunnel = await self.app.api_client.create_tunnel(
                local_port=port,
                subdomain=subdomain if subdomain else None
            )
            
            # Auto-connect if port is available
            if await self._is_port_available(port):
                try:
                    # Ensure FRP client is installed
                    if await self.app.frp_client_manager.ensure_frpc_installed():
                        # Start the tunnel
                        await self.app.frp_client_manager.start_tunnel(tunnel, port)
                        self.notify(
                            f"Tunnel created and connected: {tunnel['full_url']}",
                            severity="success",
                            timeout=4
                        )
                    else:
                        self.notify(
                            f"Tunnel created: {tunnel['full_url']} (FRP client install failed)",
                            severity="warning",
                            timeout=4
                        )
                except Exception as conn_err:
                    self.notify(
                        f"Tunnel created but connection failed: {str(conn_err)}",
                        severity="warning",
                        timeout=4
                    )
            else:
                self.notify(
                    f"Tunnel created: {tunnel['full_url']} (Port {port} not available)",
                    severity="info",
                    timeout=4
                )
            
            # Refresh the dashboard before popping screen
            dashboard = self.app.get_screen("dashboard")
            if dashboard:
                await dashboard.load_tunnels()
            self.app.pop_screen()
        except Exception as e:
            self.notify(f"Failed to create tunnel: {str(e)}", severity="error", timeout=3)
    
    async def _is_port_available(self, port: int) -> bool:
        """Check if a local port is listening"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0  # Port is open if connect succeeds
        finally:
            sock.close()
    
    @on(Button.Pressed, "#cancel")
    def handle_cancel(self, event: Button.Pressed = None) -> None:
        """Cancel and go back"""
        self.app.pop_screen()
    
    async def action_create(self) -> None:
        """Keyboard shortcut for create"""
        await self.handle_create(None)
    
    def action_cancel(self) -> None:
        """Keyboard shortcut for cancel"""
        self.app.pop_screen()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields"""
        if event.input.id in ["port", "subdomain"]:
            await self.handle_create(None)
    
    async def on_key(self, event) -> None:
        """Handle key presses"""
        if event.key == "enter":
            # If not in an input field, trigger create
            focused = self.app.focused
            if not hasattr(focused, '__class__') or focused.__class__.__name__ != 'Input':
                await self.handle_create(None)


class EditTunnelPortScreen(Screen):
    """Edit tunnel local port screen"""
    
    CSS = """
    EditTunnelPortScreen {
        align: center middle;
    }
    
    #edit-panel {
        width: 60;
        padding: 2;
    }
    
    #button-container {
        margin-top: 2;
        height: 3;
    }
    
    #button-container Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "save", "Save", show=True),
    ]
    
    def __init__(self, tunnel_data: dict):
        super().__init__()
        self.tunnel_data = tunnel_data
        self.tunnel_id = tunnel_data.get("id")
        self.subdomain = tunnel_data.get("subdomain")
        self.current_port = tunnel_data.get("local_port")
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Center():
            with Middle():
                with Container(id="edit-panel"):
                    yield Static(f"[bold cyan]═══ Edit Tunnel Port ═══[/bold cyan]\n")
                    yield Static(f"[dim]Tunnel: {self.subdomain}.tunnel.ovream.com[/dim]\n")
                    
                    yield Label("Local Port:")
                    yield Input(
                        id="port",
                        value=str(self.current_port) if self.current_port else ""
                    )
                    yield Static(
                        "[dim]Enter the local port for this tunnel\n"
                        "Leave empty to disconnect[/dim]\n"
                    )
                    
                    # Add spacing before buttons
                    yield Static("")
                    
                    with Horizontal(id="button-container"):
                        yield Button("Save", variant="primary", id="save")
                        yield Button("Cancel", variant="default", id="cancel")
        
        yield Footer()
    
    @on(Button.Pressed, "#save")
    async def handle_save(self, event: Button.Pressed = None) -> None:
        """Save the port change"""
        port_str = self.query_one("#port").value.strip()
        
        if port_str:
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    raise ValueError("Port must be between 1 and 65535")
            except ValueError as e:
                self.notify(str(e), severity="error", timeout=2)
                return
        else:
            port = None
        
        try:
            # Update the tunnel's local port
            await self.app.api_client.update_tunnel_port(self.tunnel_id, port)
            
            # If port was set, try to connect
            if port:
                if await self._is_port_available(port):
                    try:
                        await self.app.frp_client_manager.start_tunnel(self.tunnel_data, port)
                        self.notify(f"Port updated and tunnel connected", severity="success", timeout=2)
                    except:
                        self.notify(f"Port updated but connection failed", severity="warning", timeout=2)
                else:
                    self.notify(f"Port updated (not available yet)", severity="info", timeout=2)
            else:
                # Stop the tunnel if it was running
                await self.app.frp_client_manager.stop_tunnel(self.tunnel_id)
                self.notify("Tunnel disconnected", severity="info", timeout=2)
            
            # Refresh dashboard
            dashboard = self.app.get_screen("dashboard")
            if dashboard:
                await dashboard.load_tunnels()
            
            self.app.pop_screen()
        except Exception as e:
            self.notify(f"Failed to update port: {str(e)}", severity="error", timeout=3)
    
    async def _is_port_available(self, port: int) -> bool:
        """Check if a local port is listening"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0
        finally:
            sock.close()
    
    @on(Button.Pressed, "#cancel")
    def handle_cancel(self, event: Button.Pressed = None) -> None:
        """Cancel and go back"""
        self.app.pop_screen()
    
    async def action_save(self) -> None:
        """Keyboard shortcut for save"""
        await self.handle_save(None)
    
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
        "edit_tunnel_port": EditTunnelPortScreen,
    }
    
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.api_client = APIClient()
        self.frp_client_manager = FRPClientManager(self.api_client)
    
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
        
        self.notify(f"Welcome, {self.config.username}!", severity="success", timeout=2)
    
    async def on_shutdown(self) -> None:
        """Cleanup on shutdown"""
        # Stop all running tunnels
        await self.frp_client_manager.stop_all_tunnels()
        # Close API client
        await self.api_client.__aexit__(None, None, None)


def main():
    """Main entry point"""
    app = TunnelApp()
    app.run()


if __name__ == "__main__":
    main()