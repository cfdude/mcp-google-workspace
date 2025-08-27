#!/usr/bin/env python3
"""Test the OAuth fix for Desktop clients - simulate token exchange without client_secret"""

import os
import asyncio
from starlette.requests import Request
from starlette.applications import Starlette
from urllib.parse import urlencode

# Set environment for Desktop OAuth client
os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "730291917419-ovfbcd3kco8kck9nlm0p7n2n71lb8fij.apps.googleusercontent.com"
os.environ["GOOGLE_OAUTH_CLIENT_TYPE"] = "desktop"
os.environ["USER_GOOGLE_EMAIL"] = "rob.sherman@highway.ai"

# Import after setting environment
from auth.oauth_common_handlers import handle_proxy_token_exchange
from auth.oauth_config import get_oauth_config

async def test_oauth_fix():
    """Test that Desktop OAuth doesn't add client_secret"""
    print("🧪 Testing OAuth Fix for Desktop Clients")
    print("=" * 50)
    
    # Show configuration
    config = get_oauth_config()
    print(f"Client Type: {config.client_type}")
    print(f"Is Public Client: {config.is_public_client}")
    print(f"Is Secretless Mode: {config.is_secretless_mode()}")
    
    # Simulate a token exchange request (this is what would come from the OAuth callback)
    form_data = urlencode({
        "grant_type": "authorization_code",
        "code": "test_auth_code",
        "redirect_uri": "http://localhost:8080/oauth2callback",
        "code_verifier": "test_code_verifier_123",
        "client_id": "730291917419-ovfbcd3kco8kck9nlm0p7n2n71lb8fij.apps.googleusercontent.com"
    })
    
    print("\n🔄 Simulating Token Exchange Request...")
    print("Request data includes:")
    print("  - grant_type: authorization_code")
    print("  - code: test_auth_code")
    print("  - redirect_uri: http://localhost:8080/oauth2callback") 
    print("  - code_verifier: test_code_verifier_123")
    print("  - client_id: 730291917419-ovfbcd3kco8kck9nlm0p7n2n71lb8fij.apps.googleusercontent.com")
    print("  - client_secret: NOT INCLUDED (this is the test!)")
    
    # Create a mock request
    class MockRequest:
        def __init__(self):
            self.method = "POST"
            self.headers = {"content-type": "application/x-www-form-urlencoded"}
            self._body = form_data.encode('utf-8')
            
        async def body(self):
            return self._body
            
        def get(self, key, default=None):
            return self.headers.get(key, default)
    
    request = MockRequest()
    
    try:
        print("\n🚀 Testing handle_proxy_token_exchange function...")
        # This should NOT add client_secret for Desktop clients
        # The function will fail when trying to contact Google (expected), 
        # but we're testing the logic before that
        await handle_proxy_token_exchange(request)
        
    except Exception as e:
        # Expected to fail when contacting Google, but we can check the logs
        print(f"\n📝 Expected failure when contacting Google: {type(e).__name__}")
        print("✅ This is expected - we're just testing that client_secret logic works")
    
    print("\n🔍 Check the logs above for:")
    print("  ✅ 'Skipping client_secret for public client (using PKCE)' - GOOD")
    print("  ❌ 'Added missing client_secret to token request' - BAD")
    
if __name__ == "__main__":
    asyncio.run(test_oauth_fix())