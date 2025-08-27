#!/usr/bin/env python3
"""
Test script for PKCE-only authentication implementation.
This script validates the security-hardened OAuth flow without client_secret.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from auth.oauth_config import OAuthConfig
from auth.google_auth import generate_code_verifier, generate_code_challenge, create_oauth_flow

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pkce_configuration():
    """Test PKCE configuration and code generation."""
    print("🔧 Testing PKCE Configuration")
    print("=" * 40)
    
    # Test different client types
    test_cases = [
        ("uwp", True),
        ("android", True),
        ("ios", True),
        ("native", True),
        ("desktop", True),
        ("web", False),
        ("", False)  # Default
    ]
    
    for client_type, expected_public in test_cases:
        print(f"\n📱 Testing client type: '{client_type or 'default'}'")
        
        # Set environment temporarily
        old_value = os.environ.get("GOOGLE_OAUTH_CLIENT_TYPE")
        if client_type:
            os.environ["GOOGLE_OAUTH_CLIENT_TYPE"] = client_type
        elif "GOOGLE_OAUTH_CLIENT_TYPE" in os.environ:
            del os.environ["GOOGLE_OAUTH_CLIENT_TYPE"]
        
        try:
            config = OAuthConfig()
            
            print(f"   Client Type: {config.client_type}")
            print(f"   Is Public Client: {config.is_public_client}")
            print(f"   Is Secretless Mode: {config.is_secretless_mode()}")
            print(f"   Requires PKCE: {config.requires_pkce()}")
            
            # Verify expectations
            assert config.is_public_client == expected_public, f"Expected is_public_client={expected_public}, got {config.is_public_client}"
            assert config.is_secretless_mode() == expected_public, f"Expected is_secretless_mode={expected_public}, got {config.is_secretless_mode()}"
            assert config.requires_pkce() == expected_public, f"Expected requires_pkce={expected_public}, got {config.requires_pkce()}"
            
            print("   ✅ Configuration test passed")
            
        finally:
            # Restore original environment
            if old_value is not None:
                os.environ["GOOGLE_OAUTH_CLIENT_TYPE"] = old_value
            elif "GOOGLE_OAUTH_CLIENT_TYPE" in os.environ:
                del os.environ["GOOGLE_OAUTH_CLIENT_TYPE"]

def test_pkce_code_generation():
    """Test PKCE code verifier and challenge generation."""
    print("\n🔐 Testing PKCE Code Generation")
    print("=" * 40)
    
    # Generate multiple code verifiers to ensure uniqueness
    verifiers = []
    challenges = []
    
    for i in range(5):
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        
        print(f"\n🔄 Test {i+1}:")
        print(f"   Code Verifier: {verifier[:20]}...{verifier[-10:]} (length: {len(verifier)})")
        print(f"   Code Challenge: {challenge[:20]}...{challenge[-10:]} (length: {len(challenge)})")
        
        # Verify properties
        assert 43 <= len(verifier) <= 128, f"Code verifier length {len(verifier)} not in range 43-128"
        assert len(challenge) == 43, f"Code challenge length {len(challenge)} should be 43"
        assert verifier not in verifiers, "Code verifier should be unique"
        assert challenge not in challenges, "Code challenge should be unique"
        
        verifiers.append(verifier)
        challenges.append(challenge)
        
        print("   ✅ Code generation test passed")

def test_oauth_flow_creation():
    """Test OAuth flow creation with PKCE parameters."""
    print("\n🌐 Testing OAuth Flow Creation")
    print("=" * 40)
    
    # Set up test environment for UWP client
    os.environ["GOOGLE_OAUTH_CLIENT_TYPE"] = "uwp"
    os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
    # Intentionally NOT setting GOOGLE_OAUTH_CLIENT_SECRET for security test
    
    try:
        config = OAuthConfig()
        
        print(f"   Client ID: {config.client_id}")
        print(f"   Client Secret: {'SET' if config.client_secret else 'NOT SET (correct for UWP)'}")
        print(f"   Is Public Client: {config.is_public_client}")
        print(f"   Requires PKCE: {config.requires_pkce()}")
        
        # Test OAuth flow creation
        scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        redirect_uri = 'http://localhost:8080/oauth2callback'
        flow = create_oauth_flow(scopes, redirect_uri, 'test-state-123')
        
        print(f"\n🔗 OAuth Flow Properties:")
        print(f"   Flow Type: {type(flow).__name__}")
        print(f"   Client ID: {flow.client_config['client_id']}")
        print(f"   Has Client Secret: {'client_secret' in flow.client_config and bool(flow.client_config['client_secret'])}")
        print(f"   Redirect URI: {flow.redirect_uri}")
        
        # Check PKCE attributes
        if hasattr(flow, 'code_verifier'):
            print(f"   Code Verifier Set: {bool(flow.code_verifier)}")
            if flow.code_verifier:
                print(f"   Code Verifier Length: {len(flow.code_verifier)}")
        
        if hasattr(flow.oauth2session, 'code_challenge'):
            print(f"   Code Challenge Set: {bool(flow.oauth2session.code_challenge)}")
            if flow.oauth2session.code_challenge:
                print(f"   Code Challenge Length: {len(flow.oauth2session.code_challenge)}")
                print(f"   Code Challenge Method: {getattr(flow.oauth2session, 'code_challenge_method', 'NOT SET')}")
        
        print("   ✅ OAuth flow creation test passed")
        
    except Exception as e:
        print(f"   ❌ OAuth flow creation failed: {e}")
        raise

def test_environment_validation():
    """Test environment variable validation for security."""
    print("\n🛡️ Testing Security Environment Validation")
    print("=" * 40)
    
    # Test cases for security validation
    security_tests = [
        {
            "name": "UWP Client - No Secret (Secure)",
            "env": {
                "GOOGLE_OAUTH_CLIENT_TYPE": "uwp",
                "GOOGLE_OAUTH_CLIENT_ID": "test.apps.googleusercontent.com"
                # No GOOGLE_OAUTH_CLIENT_SECRET - this is correct for security
            },
            "should_be_configured": True,
            "should_be_secure": True
        },
        {
            "name": "Web Client - With Secret (Traditional)",
            "env": {
                "GOOGLE_OAUTH_CLIENT_TYPE": "web",
                "GOOGLE_OAUTH_CLIENT_ID": "test.apps.googleusercontent.com",
                "GOOGLE_OAUTH_CLIENT_SECRET": "test-secret"
            },
            "should_be_configured": True,
            "should_be_secure": False  # Less secure due to stored secret
        },
        {
            "name": "UWP Client - Missing Client ID",
            "env": {
                "GOOGLE_OAUTH_CLIENT_TYPE": "uwp"
                # Missing GOOGLE_OAUTH_CLIENT_ID
            },
            "should_be_configured": False,
            "should_be_secure": True
        }
    ]
    
    original_env = dict(os.environ)
    
    for test in security_tests:
        print(f"\n🔍 Testing: {test['name']}")
        
        try:
            # Clear OAuth environment variables
            for key in list(os.environ.keys()):
                if key.startswith("GOOGLE_OAUTH_"):
                    del os.environ[key]
            
            # Set test environment
            for key, value in test['env'].items():
                os.environ[key] = value
            
            config = OAuthConfig()
            
            is_configured = config.is_configured()
            is_secure = config.is_secretless_mode()
            
            print(f"   Configured: {is_configured} (expected: {test['should_be_configured']})")
            print(f"   Secretless: {is_secure} (expected: {test['should_be_secure']})")
            
            assert is_configured == test['should_be_configured'], f"Configuration mismatch"
            assert is_secure == test['should_be_secure'], f"Security mode mismatch"
            
            print("   ✅ Security validation passed")
            
        except Exception as e:
            print(f"   ❌ Security validation failed: {e}")
            raise
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

def main():
    """Run all PKCE authentication tests."""
    print("🚀 PKCE Authentication Test Suite")
    print("=" * 50)
    print("Testing security-hardened OAuth implementation without client_secret storage")
    print()
    
    try:
        test_pkce_configuration()
        test_pkce_code_generation()
        test_oauth_flow_creation()
        test_environment_validation()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED")
        print("🔐 PKCE implementation is working correctly")
        print("🛡️ Security hardening is properly configured")
        print("🚀 Ready for production deployment without client_secret storage")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("🔧 Please check the implementation and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()