"""
Local authentication server for receiving API key from browser
"""
import asyncio
import json
import uuid
from aiohttp import web
from typing import Optional


class AuthServer:
    def __init__(self, port: int = 8899):
        self.port = port
        self.app = web.Application()
        self.api_key: Optional[str] = None
        self.session_id = str(uuid.uuid4())
        self.runner = None
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup the routes for the auth server"""
        self.app.router.add_post('/callback', self.handle_callback)
        self.app.router.add_get('/status', self.handle_status)
        self.app.router.add_options('/callback', self.handle_options)
    
    async def handle_options(self, request):
        """Handle CORS preflight requests"""
        return web.Response(
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            }
        )
    
    async def handle_callback(self, request):
        """Handle callback from browser with API key"""
        try:
            data = await request.json()
            if data.get('session_id') == self.session_id:
                self.api_key = data.get('api_key')
                return web.json_response(
                    {"status": "success", "message": "API key received"},
                    headers={'Access-Control-Allow-Origin': '*'}
                )
            else:
                return web.json_response(
                    {"status": "error", "message": "Invalid session"},
                    status=400,
                    headers={'Access-Control-Allow-Origin': '*'}
                )
        except Exception as e:
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500,
                headers={'Access-Control-Allow-Origin': '*'}
            )
    
    async def handle_status(self, request):
        """Check if API key has been received"""
        return web.json_response({
            "received": self.api_key is not None,
            "session_id": self.session_id
        })
    
    async def start(self):
        """Start the auth server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, 'localhost', self.port)
        await site.start()
    
    async def stop(self):
        """Stop the auth server"""
        if self.runner:
            await self.runner.cleanup()
    
    async def wait_for_auth(self, timeout: int = 120) -> Optional[str]:
        """Wait for authentication with timeout"""
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.api_key:
                return self.api_key
            await asyncio.sleep(1)
        return None
    
    def get_auth_url(self) -> str:
        """Get the authentication URL to open in browser"""
        callback_url = f"http://localhost:{self.port}/callback"
        return f"https://tunnel.ovream.com/cli-auth?session={self.session_id}&callback={callback_url}"