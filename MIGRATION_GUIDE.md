# Migration Guide: Traditional OAuth to PKCE-Only Authentication

This guide helps you migrate from traditional OAuth (with client_secret storage) to security-hardened PKCE-only authentication without secret storage.

## 🚨 Why Migrate?

**Security Issue**: Traditional OAuth implementations store `client_secret` in:
- macOS Keychain
- Environment variables 
- Configuration files
- Container secrets

This violates OAuth 2.0 security best practices for public clients and creates compliance issues for organization-wide deployments.

**Solution**: PKCE-only authentication eliminates permanent secret storage while maintaining secure, long-lasting sessions.

## 📋 Pre-Migration Checklist

### ✅ Current State Assessment
Before starting, verify your current setup:

```bash
# Check current OAuth configuration
echo "Current Client ID: $GOOGLE_OAUTH_CLIENT_ID"
echo "Current Client Secret: ${GOOGLE_OAUTH_CLIENT_SECRET:+SET}"
echo "Current Client Type: ${GOOGLE_OAUTH_CLIENT_TYPE:-web}"
```

### ✅ Backup Current Credentials
Save your existing OAuth configuration:

```bash
# Export current environment
env | grep GOOGLE_OAUTH > oauth_backup.env

# Or save from your deployment configuration
kubectl get secret workspace-mcp-oauth -o yaml > oauth_backup.yaml
```

## 🔄 Migration Steps

### Step 1: Create New OAuth 2.0 Credentials (Google Cloud Console)

1. **Navigate to Google Cloud Console**:
   - Go to https://console.cloud.google.com
   - Select your project
   - Navigate to "APIs & Services" → "Credentials"

2. **Create New Desktop Application Credentials**:
   - Click "+ CREATE CREDENTIALS" → "OAuth 2.0 Client IDs"
   - **Important**: Select "Desktop application" (NOT "Web application")
   - Name it: "Workspace MCP PKCE Client" 
   - Click "CREATE"

3. **Configure Authorized Redirect URIs**:
   - Edit the new OAuth client
   - Add redirect URIs:
     ```
     http://localhost:8000/oauth2callback
     http://localhost:8080/oauth2callback
     ```
   - Add any custom URIs you use
   - Save changes

4. **Verify No Client Secret**:
   - ✅ Client secret should be empty/grayed out
   - ✅ Only Client ID should be provided
   - ❌ If you see a client_secret, you selected the wrong application type

### Step 2: Update Environment Configuration

#### For Docker Deployments:
```bash
# Update your .env file
GOOGLE_OAUTH_CLIENT_ID=your-new-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_TYPE=desktop
# Remove GOOGLE_OAUTH_CLIENT_SECRET entirely
USER_GOOGLE_EMAIL=your-email@yourdomain.com
```

#### For Kubernetes Deployments:
```yaml
# Update your secret or configmap
apiVersion: v1
kind: Secret
metadata:
  name: workspace-mcp-oauth
type: Opaque
data:
  GOOGLE_OAUTH_CLIENT_ID: <base64-encoded-client-id>
  GOOGLE_OAUTH_CLIENT_TYPE: ZGVza3RvcA==  # base64 for "desktop"
  USER_GOOGLE_EMAIL: <base64-encoded-email>
  # GOOGLE_OAUTH_CLIENT_SECRET: REMOVE THIS ENTIRELY
```

#### For Development:
```bash
export GOOGLE_OAUTH_CLIENT_ID="your-new-client-id.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_TYPE="desktop"
export USER_GOOGLE_EMAIL="your-email@yourdomain.com"
unset GOOGLE_OAUTH_CLIENT_SECRET  # Remove entirely
```

### Step 3: Test New Configuration

Run the validation test:
```bash
# Test the new PKCE configuration
python test_pkce_auth.py
```

Expected output:
```
✅ ALL TESTS PASSED
🔐 PKCE implementation is working correctly
🛡️ Security hardening is properly configured
🚀 Ready for production deployment without client_secret storage
```

### Step 4: Deploy New Configuration

#### Docker Deployment:
```bash
# Rebuild and deploy with new environment
docker build -t workspace-mcp:latest .
docker run -d --env-file .env workspace-mcp:latest
```

#### Kubernetes Deployment:
```bash
# Apply new secret and restart deployment
kubectl apply -f oauth-secret.yaml
kubectl rollout restart deployment/workspace-mcp
kubectl rollout status deployment/workspace-mcp
```

#### Local Development:
```bash
# Start server with new environment
uv run main.py
```

### Step 5: Verify Authentication Flow

1. **Start the server** and trigger OAuth flow
2. **Check logs** for PKCE indicators:
   ```
   Using PKCE code_verifier for token exchange (secretless mode)
   Added PKCE parameters for public client type: desktop
   ```
3. **Verify session persistence** - tokens should still work after restart
4. **Test all Google Workspace tools** to ensure functionality

## 🔍 Troubleshooting

### Issue: "OAuth client not configured"
```bash
# Check environment variables
env | grep GOOGLE_OAUTH

# Verify client ID format
echo $GOOGLE_OAUTH_CLIENT_ID | grep -E '[0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com'
```

### Issue: "client_secret is required"
This means you're still using old credentials or wrong client type:
```bash
# Verify client type is set correctly
echo "Client Type: $GOOGLE_OAUTH_CLIENT_TYPE"  # Should be "desktop"

# Check if old client_secret is still set
echo "Client Secret: ${GOOGLE_OAUTH_CLIENT_SECRET:+STILL_SET}"  # Should be empty
```

### Issue: "Invalid redirect URI"
Update your Google Cloud Console OAuth client:
1. Go to OAuth 2.0 Client IDs
2. Edit your Desktop application client
3. Add the redirect URI you're using
4. Save changes

### Issue: "PKCE validation failed"
This typically means mixing old and new configurations:
```bash
# Clear all OAuth environment variables and set only the new ones
unset GOOGLE_OAUTH_CLIENT_SECRET
export GOOGLE_OAUTH_CLIENT_TYPE="desktop"
export GOOGLE_OAUTH_CLIENT_ID="your-new-client-id"
```

## 📊 Verification Checklist

After migration, verify these security improvements:

- [ ] No `GOOGLE_OAUTH_CLIENT_SECRET` in environment variables
- [ ] No `client_secret` in configuration files
- [ ] No secrets stored in macOS Keychain for OAuth
- [ ] OAuth client type shows as "desktop" or public client
- [ ] PKCE parameters appear in OAuth flow logs
- [ ] Authentication still works for all Google Workspace tools
- [ ] Sessions persist across server restarts
- [ ] Multiple users can authenticate without secret sharing

## 🔒 Security Benefits Achieved

### Before Migration (Traditional OAuth):
- ❌ `client_secret` stored in system keychain
- ❌ Secret shared across all deployments  
- ❌ Compliance issues for organization-wide deployment
- ❌ Secret rotation requires updating all instances

### After Migration (PKCE-Only):
- ✅ No permanent secret storage
- ✅ Each authentication uses unique PKCE codes
- ✅ Compliant with OAuth 2.0 security best practices
- ✅ Safe for organization-wide deployment
- ✅ No secret rotation needed

## 🚀 Next Steps

1. **Monitor the new setup** for a few days to ensure stability
2. **Update your deployment documentation** with new environment variables
3. **Train your team** on the new secretless OAuth approach  
4. **Decommission old OAuth credentials** in Google Cloud Console
5. **Consider enabling this by default** for all new deployments

## 📞 Support

If you encounter issues during migration:

1. **Check the logs** for specific error messages
2. **Run the test suite** to validate configuration
3. **Compare with working examples** in the documentation
4. **Verify Google Cloud Console settings** match the guide

## ⚡ Quick Migration Commands

For experienced users, here's the condensed migration:

```bash
# 1. Get new Desktop OAuth credentials from Google Cloud Console
# 2. Update environment (remove secret, add type)
unset GOOGLE_OAUTH_CLIENT_SECRET
export GOOGLE_OAUTH_CLIENT_TYPE="desktop"  
export GOOGLE_OAUTH_CLIENT_ID="new-client-id.apps.googleusercontent.com"

# 3. Test configuration
python test_pkce_auth.py

# 4. Deploy
uv run main.py
```

Migration complete! 🎉