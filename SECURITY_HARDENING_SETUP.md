# Security Hardening Setup Guide: PKCE-Only Authentication

## Overview

This guide implements OAuth 2.0 PKCE-only authentication without storing client_secret, addressing the security vulnerability where traditional OAuth flows require permanent storage of sensitive client credentials in system keychains.

**Security Benefits:**
- ✅ No permanent storage of client_secret in macOS Keychain or other credential stores
- ✅ Follows OAuth 2.0 RFC 7636 PKCE specification for public clients
- ✅ Eliminates credential theft vulnerability for desktop/mobile applications
- ✅ Enables organization-wide deployment without compliance issues
- ✅ Maintains long-lasting sessions without storing sensitive secrets

## Google Cloud Console Setup

### Step 1: Create UWP OAuth 2.0 Credentials

1. **Navigate to Google Cloud Console**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Select your project or create a new one

2. **Enable Required APIs**
   - Navigate to **APIs & Services** → **Library**
   - Enable the following APIs:
     - Gmail API
     - Google Drive API
     - Google Calendar API
     - Google Docs API
     - Google Sheets API
     - Google Slides API
     - Google Forms API
     - Google Chat API
     - Google Tasks API
     - Custom Search JSON API (if using search features)

3. **Configure OAuth Consent Screen**
   - Navigate to **APIs & Services** → **OAuth consent screen**
   - Choose **External** user type (for business use across organization)
   - Fill in required fields:
     - App name: "Your Organization - Google Workspace MCP"
     - User support email: your business email
     - Developer contact information: your business email
   - Add scopes for all enabled APIs
   - Add test users or publish the app for production use

4. **Create UWP OAuth 2.0 Client**
   - Navigate to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth 2.0 Client ID**
   - **CRITICAL**: Select **Desktop application** as the application type
   - Name: "Google Workspace MCP - UWP Client"
   - **Do NOT download the JSON file** - it will contain a client_secret that we don't want to use

5. **Extract Client ID Only**
   - After creation, click on the credential name to view details
   - **Copy only the Client ID** (format: `xxxxx.apps.googleusercontent.com`)
   - **Ignore the Client Secret** - this is the key security improvement
   - Note the redirect URI: `http://localhost` (default for desktop apps)

### Step 2: Configure Redirect URIs

For desktop applications using PKCE, Google automatically configures these redirect URIs:
- `http://localhost`
- `http://127.0.0.1`
- Custom port variations (e.g., `http://localhost:8000`)

If you need to add custom redirect URIs:
1. In the OAuth 2.0 Client details page
2. Click **Edit** 
3. Add authorized redirect URIs:
   - `http://localhost:8000/oauth2callback`
   - `http://127.0.0.1:8000/oauth2callback`
   - Any other custom URIs your deployment requires

## Environment Configuration

### Required Environment Variables

```bash
# OAuth Configuration - Security Hardened
GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_TYPE="uwp"                    # Enables PKCE-only mode
# DO NOT SET GOOGLE_OAUTH_CLIENT_SECRET - intentionally omitted for security

# Server Configuration
WORKSPACE_MCP_BASE_URI="http://localhost"
WORKSPACE_MCP_PORT="8000"
GOOGLE_OAUTH_REDIRECT_URI="http://localhost:8000/oauth2callback"

# User Configuration (optional, recommended for business deployment)
USER_GOOGLE_EMAIL="rob.sherman@highway.ai"       # Your business email

# OAuth 2.1 Configuration (recommended for multi-user environments)
MCP_ENABLE_OAUTH21="true"
WORKSPACE_MCP_STATELESS_MODE="true"

# Development Only - Set to "0" for production
OAUTHLIB_INSECURE_TRANSPORT="0"
```

### Supported Client Types

The system supports these public client types for PKCE-only authentication:

| Client Type | Environment Value | Use Case |
|-------------|-------------------|----------|
| UWP | `uwp` | Universal Windows Platform apps |
| Android | `android` | Android mobile applications |
| iOS | `ios` | iOS mobile applications |
| Native | `native` | General native applications |

All public client types automatically:
- Enable PKCE flow with SHA256 code challenge
- Skip client_secret requirement
- Generate secure code verifiers (96-byte random)
- Use `authorization_code` grant type with PKCE extension

## Deployment Examples

### Docker Compose

```yaml
version: '3.8'
services:
  workspace-mcp:
    image: workspace-mcp:latest
    ports:
      - "8000:8000"
    environment:
      GOOGLE_OAUTH_CLIENT_ID: "your-client-id.apps.googleusercontent.com"
      GOOGLE_OAUTH_CLIENT_TYPE: "uwp"
      USER_GOOGLE_EMAIL: "rob.sherman@highway.ai"
      WORKSPACE_MCP_BASE_URI: "http://localhost"
      WORKSPACE_MCP_PORT: "8000"
      MCP_ENABLE_OAUTH21: "true"
      WORKSPACE_MCP_STATELESS_MODE: "true"
      OAUTHLIB_INSECURE_TRANSPORT: "0"
    command: ["uv", "run", "python", "main.py", "--transport", "streamable-http"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: workspace-mcp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: workspace-mcp
  template:
    metadata:
      labels:
        app: workspace-mcp
    spec:
      containers:
      - name: workspace-mcp
        image: workspace-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: GOOGLE_OAUTH_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: workspace-mcp-oauth
              key: client-id
        - name: GOOGLE_OAUTH_CLIENT_TYPE
          value: "uwp"
        - name: USER_GOOGLE_EMAIL
          value: "rob.sherman@highway.ai"
        - name: WORKSPACE_MCP_BASE_URI
          value: "https://your-domain.com"
        - name: WORKSPACE_MCP_PORT
          value: "8000"
        - name: MCP_ENABLE_OAUTH21
          value: "true"
        - name: WORKSPACE_MCP_STATELESS_MODE
          value: "true"
        - name: OAUTHLIB_INSECURE_TRANSPORT
          value: "0"
```

### Local Development

```bash
# Set environment variables
export GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_TYPE="uwp"
export USER_GOOGLE_EMAIL="rob.sherman@highway.ai"
export WORKSPACE_MCP_BASE_URI="http://localhost"
export WORKSPACE_MCP_PORT="8000"
export MCP_ENABLE_OAUTH21="true"
export WORKSPACE_MCP_STATELESS_MODE="true"
export OAUTHLIB_INSECURE_TRANSPORT="1"  # Development only

# Start server
uv run python main.py --transport streamable-http
```

## Authentication Flow

### PKCE Flow Overview

1. **Authorization Request**
   - Client generates random code_verifier (96 bytes, base64url-encoded)
   - Client generates code_challenge = SHA256(code_verifier), base64url-encoded
   - Client redirects user to Google OAuth with code_challenge and method=S256

2. **Authorization Grant**
   - User authenticates with Google and grants permissions
   - Google redirects back with authorization code
   - **No client_secret is transmitted or stored**

3. **Token Exchange**
   - Client exchanges authorization code for access token
   - Includes original code_verifier in token request
   - Google validates code_verifier against stored code_challenge
   - Returns access/refresh tokens without requiring client_secret

### Security Advantages

- **No Stored Secrets**: client_secret is never generated, transmitted, or stored
- **Replay Protection**: Each code_verifier is unique and single-use
- **Interception Resistance**: Authorization codes are useless without matching code_verifier
- **Compliance**: Follows OAuth 2.0 RFC 7636 and OAuth 2.1 security guidelines

## Verification

### Test the Configuration

1. **Start the server with debug logging:**
   ```bash
   GOOGLE_OAUTH_CLIENT_TYPE=uwp uv run python main.py --transport streamable-http
   ```

2. **Verify PKCE mode is enabled:**
   Look for these log messages:
   ```
   🔧 Google Workspace MCP Server
   ===================================
   ⚙️ Active Configuration:
      - GOOGLE_OAUTH_CLIENT_TYPE: uwp
   🔐 PKCE-only mode enabled (secretless authentication)
   ```

3. **Test authentication:**
   - Navigate to `http://localhost:8000/oauth2callback`
   - Should redirect to Google OAuth with PKCE parameters
   - Check URL contains `code_challenge` and `code_challenge_method=S256`

4. **Verify no client_secret in logs:**
   - Debug logs should show "Using PKCE code_verifier for token exchange (secretless mode)"
   - Should NOT see any client_secret values in logs or error messages

## Troubleshooting

### Common Issues

1. **"Client authentication failed" error**
   - Ensure GOOGLE_OAUTH_CLIENT_TYPE is set to "uwp" or another public client type
   - Verify the client was created as "Desktop application" in Google Cloud Console
   - Check that client_secret environment variable is NOT set

2. **"Invalid redirect URI" error**
   - Ensure redirect URI matches exactly: `http://localhost:8000/oauth2callback`
   - For production, add your domain's redirect URI to Google Cloud Console

3. **"PKCE verification failed" error**
   - This indicates a bug in code_verifier generation or storage
   - Check server logs for code_verifier/code_challenge generation messages

### Security Validation

To verify your deployment is secure:

1. **Check environment variables:**
   ```bash
   env | grep GOOGLE_OAUTH | grep -v CLIENT_SECRET
   ```
   Should NOT return any CLIENT_SECRET variables

2. **Check credential storage:**
   - No client_secret should exist in macOS Keychain
   - No client_secret files should exist in credential directories

3. **Check network traffic:**
   - OAuth requests should contain `code_challenge` parameter
   - Token exchange should contain `code_verifier` parameter
   - No `client_secret` should appear in any HTTP requests

## Production Considerations

### Security Best Practices

1. **Environment Variable Management**
   - Use secret management systems (Kubernetes secrets, Docker secrets, etc.)
   - Never commit OAuth client IDs to version control
   - Rotate client credentials periodically

2. **Network Security**
   - Always use HTTPS in production (`OAUTHLIB_INSECURE_TRANSPORT=0`)
   - Implement proper TLS certificate management
   - Use secure redirect URIs (https://)

3. **Monitoring and Logging**
   - Monitor OAuth flow completion rates
   - Log authentication failures for security analysis
   - Set up alerts for unusual authentication patterns

4. **Access Control**
   - Limit OAuth scope to minimum required permissions
   - Implement proper session timeout policies
   - Use OAuth 2.1 stateless mode for scalability

This setup provides enterprise-grade security while maintaining the full functionality of the Google Workspace MCP server. The elimination of client_secret storage addresses the core security vulnerability while ensuring compliance with modern OAuth 2.0 security guidelines.