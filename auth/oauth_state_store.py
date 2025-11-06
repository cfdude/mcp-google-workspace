"""
Persistent OAuth State Store

This module provides persistent storage for OAuth state parameters to survive
process restarts during the OAuth flow. This is especially important for
Claude Desktop where the MCP server runs as a subprocess.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from threading import RLock

logger = logging.getLogger(__name__)


class PersistentOAuthStateStore:
    """
    File-based OAuth state storage that persists across process restarts.

    Stores OAuth state parameters in a JSON file to ensure they survive
    MCP server restarts during the OAuth flow.
    """

    def __init__(self, state_file_path: Optional[str] = None):
        """
        Initialize the persistent OAuth state store.

        Args:
            state_file_path: Path to the state storage file. If None, uses
                           credentials directory with oauth_states.json filename.
        """
        if state_file_path is None:
            # Use same directory as credentials
            base_dir = os.getenv("GOOGLE_MCP_CREDENTIALS_DIR")
            if not base_dir:
                home_dir = os.path.expanduser("~")
                if home_dir and home_dir != "~":
                    base_dir = os.path.join(home_dir, ".google_workspace_mcp", "credentials")
                else:
                    base_dir = os.path.join(os.getcwd(), ".credentials")

            # Ensure directory exists
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
                logger.info(f"Created OAuth state directory: {base_dir}")

            state_file_path = os.path.join(base_dir, "oauth_states.json")

        self.state_file_path = state_file_path
        self._lock = RLock()
        logger.info(f"PersistentOAuthStateStore initialized with file: {state_file_path}")

    def _load_states(self) -> Dict[str, Dict[str, Any]]:
        """Load states from disk. Caller must hold lock."""
        if not os.path.exists(self.state_file_path):
            return {}

        try:
            with open(self.state_file_path, "r") as f:
                data = json.load(f)

            # Convert ISO strings back to datetime objects
            for state_data in data.values():
                if "expires_at" in state_data and state_data["expires_at"]:
                    state_data["expires_at"] = datetime.fromisoformat(state_data["expires_at"])
                if "created_at" in state_data and state_data["created_at"]:
                    state_data["created_at"] = datetime.fromisoformat(state_data["created_at"])

            logger.debug(f"Loaded {len(data)} OAuth states from disk")
            return data

        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading OAuth states from {self.state_file_path}: {e}")
            return {}

    def _save_states(self, states: Dict[str, Dict[str, Any]]):
        """Save states to disk. Caller must hold lock."""
        try:
            # Convert datetime objects to ISO strings for JSON serialization
            serializable_states = {}
            for state, state_data in states.items():
                serializable_data = state_data.copy()
                if "expires_at" in serializable_data and serializable_data["expires_at"]:
                    serializable_data["expires_at"] = serializable_data["expires_at"].isoformat()
                if "created_at" in serializable_data and serializable_data["created_at"]:
                    serializable_data["created_at"] = serializable_data["created_at"].isoformat()
                serializable_states[state] = serializable_data

            with open(self.state_file_path, "w") as f:
                json.dump(serializable_states, f, indent=2)

            logger.debug(f"Saved {len(states)} OAuth states to disk")

        except IOError as e:
            logger.error(f"Error saving OAuth states to {self.state_file_path}: {e}")

    def _cleanup_expired_states(self, states: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Remove expired states. Caller must hold lock."""
        now = datetime.now(timezone.utc)
        cleaned_states = {}
        expired_count = 0

        for state, state_data in states.items():
            expires_at = state_data.get("expires_at")
            if expires_at and expires_at <= now:
                expired_count += 1
                logger.debug(f"Removing expired OAuth state: {state[:8]}...")
            else:
                cleaned_states[state] = state_data

        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired OAuth states")

        return cleaned_states

    def store_oauth_state(
        self,
        state: str,
        session_id: Optional[str] = None,
        expires_in_seconds: int = 600,
    ) -> None:
        """
        Persist an OAuth state value for later validation.

        Args:
            state: The OAuth state parameter
            session_id: Optional session identifier
            expires_in_seconds: How long the state is valid (default: 10 minutes)

        Raises:
            ValueError: If state is empty or expires_in_seconds is negative
        """
        if not state:
            raise ValueError("OAuth state must be provided")
        if expires_in_seconds < 0:
            raise ValueError("expires_in_seconds must be non-negative")

        with self._lock:
            # Load existing states
            states = self._load_states()

            # Clean up expired states
            states = self._cleanup_expired_states(states)

            # Add new state
            now = datetime.now(timezone.utc)
            expiry = now + timedelta(seconds=expires_in_seconds)

            states[state] = {
                "session_id": session_id,
                "expires_at": expiry,
                "created_at": now,
            }

            # Save to disk
            self._save_states(states)

            logger.debug(
                f"Stored OAuth state {state[:8]}... (expires at {expiry.isoformat()})"
            )

    def validate_and_consume_oauth_state(
        self,
        state: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate that a state value exists and consume it.

        Args:
            state: The OAuth state returned by Google
            session_id: Optional session identifier that initiated the flow

        Returns:
            Metadata associated with the state

        Raises:
            ValueError: If the state is missing, expired, or does not match the session
        """
        if not state:
            raise ValueError("Missing OAuth state parameter")

        with self._lock:
            # Load and clean up states
            states = self._load_states()
            states = self._cleanup_expired_states(states)

            # Check if state exists
            state_info = states.get(state)

            if not state_info:
                logger.error("SECURITY: OAuth callback received unknown or expired state")
                raise ValueError("Invalid or expired OAuth state parameter")

            # Validate session binding if present
            bound_session = state_info.get("session_id")
            if bound_session and session_id and bound_session != session_id:
                # Consume the state to prevent replay attempts
                del states[state]
                self._save_states(states)
                logger.error(
                    f"SECURITY: OAuth state session mismatch (expected {bound_session}, got {session_id})"
                )
                raise ValueError("OAuth state does not match the initiating session")

            # State is valid – consume it to prevent reuse
            del states[state]
            self._save_states(states)

            logger.debug(f"Validated and consumed OAuth state {state[:8]}...")
            return state_info


# Global instance
_global_state_store: Optional[PersistentOAuthStateStore] = None


def get_persistent_oauth_state_store() -> PersistentOAuthStateStore:
    """Get the global persistent OAuth state store."""
    global _global_state_store

    if _global_state_store is None:
        _global_state_store = PersistentOAuthStateStore()

    return _global_state_store
