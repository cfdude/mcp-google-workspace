# Security-Hardened OAuth Implementation TODO

This document tracks the implementation of security-hardened OAuth authentication for the Google Workspace MCP server, eliminating the need to store client secrets on user machines.

## Project Goals

- [ ] Implement true Desktop/PKCE OAuth authentication
- [ ] Eliminate permanent storage of client_secret on user computers
- [ ] Remove dependency on macOS Keychain for secret storage
- [ ] Maintain long-lasting sessions without stored secrets
- [ ] Enable org-wide deployment without security compliance issues
- [ ] Support Google business email authentication (e.g., rob.sherman@highway.ai)

## Implementation Tasks

### Phase 1: Research & Setup
- [ ] **Research and validate UWP OAuth client configuration in Google Cloud Console** ⚠️ IN PROGRESS
- [ ] **Create new OAuth 2.0 credentials as UWP client type for testing**
- [ ] Document UWP client setup process for users

### Phase 2: Core Implementation
- [ ] **Implement PKCE-only authentication mode in auth/oauth_config.py**
- [ ] **Update google_auth.py to support optional client_secret**
- [ ] **Enhance PKCE implementation with proper code_challenge generation**
- [ ] **Update OAuth token exchange to work without client_secret**
- [ ] **Add environment variable GOOGLE_OAUTH_CLIENT_TYPE support**

### Phase 3: Testing & Validation
- [ ] **Test authentication flow with UWP client credentials**
- [ ] Verify no client_secret is stored in macOS Keychain
- [ ] Test multi-user OAuth 2.1 session management
- [ ] Validate PKCE code challenge/verifier generation
- [ ] Test token refresh without client_secret

### Phase 4: Documentation & Migration
- [ ] **Update documentation with new security-hardened setup instructions**
- [ ] **Create migration guide for existing deployments**
- [ ] Update README.md with UWP client setup instructions
- [ ] Update smithery.yaml and manifest.json configurations
- [ ] Create troubleshooting guide for common issues

## Technical Details

### Key Files to Modify
- `auth/oauth_config.py` - Add PKCE-only mode detection
- `auth/google_auth.py` - Make client_secret optional
- `auth/oauth21_session_store.py` - Update session handling
- `main.py` - Add GOOGLE_OAUTH_CLIENT_TYPE support
- `smithery.yaml` - Add new configuration options
- `manifest.json` - Update user configuration schema

### Environment Variables
- `GOOGLE_OAUTH_CLIENT_TYPE` - Set to "uwp" or "android" for secretless auth
- `GOOGLE_OAUTH_CLIENT_ID` - Required (public identifier)
- `GOOGLE_OAUTH_CLIENT_SECRET` - Optional for UWP/Android clients

### Security Benefits
- ✅ No client secrets stored on user machines
- ✅ PKCE provides secure authentication without secrets
- ✅ Compliant with OAuth 2.0/2.1 public client standards
- ✅ Enables org-wide deployment
- ✅ Removes macOS Keychain dependency

## Progress Tracking

**Current Status:** Research phase - validating UWP OAuth configuration

**Next Steps:**
1. Complete UWP client setup documentation
2. Begin implementation of PKCE-only mode
3. Test secretless authentication flow

---
*Last updated: 2025-08-26*