#!/usr/bin/env python3
"""
FRP Client Manager for tunnel connections
"""
import os
import sys
import asyncio
import tempfile
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import aiohttp
import zipfile
import tarfile
import shutil


class FRPClientManager:
    """Manages FRP client binary and tunnel connections"""
    
    def __init__(self):
        self.frpc_path = None
        self.processes: Dict[str, subprocess.Popen] = {}
        self.config_dir = Path.home() / ".tunnel-cli" / "configs"
        self.bin_dir = Path.home() / ".tunnel-cli" / "bin"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        
    async def ensure_frpc_installed(self) -> bool:
        """Ensure FRP client is installed"""
        # Check if frpc already exists
        frpc_name = "frpc.exe" if platform.system() == "Windows" else "frpc"
        self.frpc_path = self.bin_dir / frpc_name
        
        if self.frpc_path.exists():
            return True
            
        # Download and install FRP client
        return await self.download_frpc()
    
    async def download_frpc(self) -> bool:
        """Download FRP client for the current platform"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Map platform to FRP release names
        if system == "darwin":
            if "arm" in machine or "aarch64" in machine:
                platform_name = "darwin_arm64"
            else:
                platform_name = "darwin_amd64"
        elif system == "linux":
            if "arm" in machine:
                platform_name = "linux_arm64"
            else:
                platform_name = "linux_amd64"
        elif system == "windows":
            platform_name = "windows_amd64"
        else:
            raise Exception(f"Unsupported platform: {system}")
        
        # FRP version
        version = "0.52.3"
        base_url = f"https://github.com/fatedier/frp/releases/download/v{version}"
        
        if system == "windows":
            filename = f"frp_{version}_{platform_name}.zip"
        else:
            filename = f"frp_{version}_{platform_name}.tar.gz"
        
        url = f"{base_url}/{filename}"
        
        try:
            # Download FRP
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download FRP: {response.status}")
                    
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz" if system != "windows" else ".zip") as tmp:
                        tmp.write(await response.read())
                        tmp_path = tmp.name
            
            # Extract
            extract_dir = self.bin_dir / "temp"
            extract_dir.mkdir(exist_ok=True)
            
            if system == "windows":
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                with tarfile.open(tmp_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            
            # Find and move frpc binary
            frpc_name = "frpc.exe" if system == "windows" else "frpc"
            extracted_frpc = None
            
            for root, dirs, files in os.walk(extract_dir):
                if frpc_name in files:
                    extracted_frpc = Path(root) / frpc_name
                    break
            
            if not extracted_frpc:
                raise Exception("FRP client binary not found in archive")
            
            # Move to final location
            shutil.move(str(extracted_frpc), str(self.frpc_path))
            
            # Make executable (Unix-like systems)
            if system != "windows":
                self.frpc_path.chmod(0o755)
            
            # Cleanup
            shutil.rmtree(extract_dir)
            os.unlink(tmp_path)
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to install FRP client: {str(e)}")
    
    async def start_tunnel(self, tunnel_data: Dict[str, Any], local_port: int) -> bool:
        """Start a tunnel connection"""
        tunnel_id = tunnel_data.get("id")
        subdomain = tunnel_data.get("subdomain")
        remote_port = tunnel_data.get("remote_port")
        
        if not all([tunnel_id, subdomain, remote_port]):
            raise ValueError("Invalid tunnel data")
        
        # Stop existing tunnel if running
        await self.stop_tunnel(tunnel_id)
        
        # Create FRP config
        config_file = self.config_dir / f"{tunnel_id}.ini"
        config_content = f"""[common]
server_addr = tunnel.ovream.com
server_port = 7000

[{subdomain}]
type = http
local_ip = 127.0.0.1
local_port = {local_port}
custom_domains = {subdomain}.tunnel.ovream.com
"""
        
        config_file.write_text(config_content)
        
        # Start FRP client
        try:
            if platform.system() == "Windows":
                # Windows: hide console window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                process = subprocess.Popen(
                    [str(self.frpc_path), "-c", str(config_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo
                )
            else:
                # Unix-like systems
                process = subprocess.Popen(
                    [str(self.frpc_path), "-c", str(config_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # Store process
            self.processes[tunnel_id] = process
            
            # Wait a bit to check if it started successfully
            await asyncio.sleep(1)
            
            if process.poll() is not None:
                # Process died
                stderr = process.stderr.read().decode() if process.stderr else ""
                raise Exception(f"FRP client failed to start: {stderr}")
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to start tunnel: {str(e)}")
    
    async def stop_tunnel(self, tunnel_id: str) -> bool:
        """Stop a tunnel connection"""
        if tunnel_id in self.processes:
            process = self.processes[tunnel_id]
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            del self.processes[tunnel_id]
            
            # Remove config file
            config_file = self.config_dir / f"{tunnel_id}.ini"
            if config_file.exists():
                config_file.unlink()
            
            return True
        return False
    
    async def stop_all_tunnels(self):
        """Stop all running tunnels"""
        tunnel_ids = list(self.processes.keys())
        for tunnel_id in tunnel_ids:
            await self.stop_tunnel(tunnel_id)
    
    def get_tunnel_status(self, tunnel_id: str) -> str:
        """Get status of a tunnel"""
        if tunnel_id in self.processes:
            process = self.processes[tunnel_id]
            if process.poll() is None:
                return "connected"
            else:
                return "disconnected"
        return "not_started"
    
    def list_active_tunnels(self) -> list:
        """List all active tunnel IDs"""
        return [
            tunnel_id for tunnel_id, process in self.processes.items()
            if process.poll() is None
        ]


# Global instance
frp_client_manager = FRPClientManager()