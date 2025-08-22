"""
API Client for tunnel service
"""
import aiohttp
import json
import ssl
import certifi
from typing import Optional, Dict, Any, List
from pathlib import Path


class APIClient:
    def __init__(self, api_url: str = "https://tunnel.ovream.com/api/v1"):
        self.api_url = api_url
        self.api_key: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        # Create SSL context with certifi certificates (works on all platforms)
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def set_api_key(self, api_key: str):
        """Set API key for authentication"""
        self.api_key = api_key
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get tokens"""
        async with self.session.post(
            f"{self.api_url}/auth/login",
            json={"username": username, "password": password}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.json()
                raise Exception(error.get("detail", "Login failed"))
    
    async def create_api_key(self, access_token: str, name: str = "TUI Client") -> str:
        """Create an API key"""
        async with self.session.post(
            f"{self.api_url}/api-keys/",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"name": name}
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["key"]
            else:
                error = await response.json()
                raise Exception(error.get("detail", "Failed to create API key"))
    
    async def get_profile(self) -> Dict[str, Any]:
        """Get user profile"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with self.session.get(
            f"{self.api_url}/cli/status",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("user", {})
            else:
                raise Exception("Invalid API key or authentication failed")
    
    async def list_tunnels(self) -> List[Dict[str, Any]]:
        """List all tunnels"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with self.session.get(
            f"{self.api_url}/cli/tunnels",
            headers=headers
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                return []
    
    async def create_tunnel(self, local_port: int, subdomain: Optional[str] = None) -> Dict[str, Any]:
        """Create a new tunnel"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        data = {"local_port": local_port}
        if subdomain:
            data["subdomain"] = subdomain
        
        async with self.session.post(
            f"{self.api_url}/cli/tunnels",
            headers=headers,
            json=data
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.json()
                raise Exception(error.get("detail", "Failed to create tunnel"))
    
    async def delete_tunnel(self, tunnel_id: str) -> bool:
        """Delete a tunnel"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with self.session.delete(
            f"{self.api_url}/cli/tunnels/{tunnel_id}",
            headers=headers
        ) as response:
            return response.status == 200
    
    async def get_quota_info(self) -> Dict[str, Any]:
        """Get quota information"""
        # Use Bearer auth for the quota endpoint
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with self.session.get(
            f"{self.api_url}/tunnels/quota/info",
            headers=headers
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                # Return default quota if endpoint fails
                return {
                    "max_tunnels": 3,
                    "used_tunnels": 0,
                    "max_custom_domains": 0,
                    "used_custom_domains": 0,
                    "can_create_tunnel": True,
                    "can_use_custom_domain": False
                }
    
    async def get_tunnel_config(self, tunnel_id: str, local_port: int) -> Dict[str, Any]:
        """Get tunnel configuration for FRP"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with self.session.get(
            f"{self.api_url}/cli/tunnels/{tunnel_id}/config",
            headers=headers,
            params={"local_port": local_port, "format": "ini"}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception("Failed to get tunnel config")
    
    async def connect_tunnel(self, tunnel_id: str, local_port: int) -> Dict[str, Any]:
        """Mark tunnel as connected"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with self.session.post(
            f"{self.api_url}/cli/tunnels/{tunnel_id}/connect",
            headers=headers,
            json={"local_port": local_port}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception("Failed to connect tunnel")
    
    async def disconnect_tunnel(self, tunnel_id: str) -> bool:
        """Mark tunnel as disconnected"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with self.session.post(
            f"{self.api_url}/cli/tunnels/{tunnel_id}/disconnect",
            headers=headers
        ) as response:
            return response.status == 200
    
    async def update_connection_status(self, tunnel_id: str, status: str):
        """Update tunnel connection status"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        
        async with self.session.put(
            f"{self.api_url}/cli/tunnels/{tunnel_id}/connection-status",
            headers=headers,
            params={"status": status}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                # Silently fail status updates
                return None
    
    async def update_tunnel_port(self, tunnel_id: str, local_port: Optional[int]) -> Dict[str, Any]:
        """Update tunnel's local port"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with self.session.put(
            f"{self.api_url}/cli/tunnels/{tunnel_id}/port",
            headers=headers,
            json={"local_port": local_port}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.json()
                raise Exception(error.get("detail", "Failed to update port"))