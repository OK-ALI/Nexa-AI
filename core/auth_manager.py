"""
Authentication Manager for Nexa AI
Handles user registration, login, and session management.
Uses PBKDF2-HMAC-SHA256 for password hashing.
Storage: LanceDB (consistent with Smart Memory system).

Author: Ali Adil Waseem
"""

import json
import hashlib
import logging
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Manages user authentication with hashed password storage.
    Uses LanceDB for persistent storage (same DB engine as Smart Memory).
    Supports registration, login, and lock/unlock session management.
    """

    TABLE_NAME = "users"

    def __init__(self, data_dir: Path):
        """
        Initialize AuthManager with LanceDB storage.
        
        Args:
            data_dir: Directory for storing data (e.g., data/)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.data_dir / "auth_db"
        self._current_user: Optional[str] = None
        self._is_locked = False
        self._db = None

        self._connect()
        self._migrate_from_json()

    def _connect(self):
        """Connect to LanceDB and ensure users table exists."""
        try:
            import lancedb
            self._db = lancedb.connect(str(self._db_path))
            logger.info(f"✅ AuthManager connected to LanceDB at {self._db_path}")
        except Exception as e:
            logger.error(f"❌ AuthManager failed to connect to LanceDB: {e}")
            raise RuntimeError(f"Could not connect to LanceDB for auth: {e}") from e

    def _get_table(self):
        """Get the users table, or None if it doesn't exist."""
        if self.TABLE_NAME in self._db.table_names():
            return self._db.open_table(self.TABLE_NAME)
        return None

    def _get_schema(self):
        """Return PyArrow schema for users table."""
        import pyarrow as pa
        return pa.schema([
            pa.field("username", pa.utf8()),
            pa.field("password_hash", pa.utf8()),
            pa.field("salt", pa.utf8()),
            pa.field("created_at", pa.utf8()),
            pa.field("last_login", pa.utf8()),
        ])

    def _create_table_with_user(self, user_record: dict):
        """Create the users table with the first user record."""
        table = self._db.create_table(
            self.TABLE_NAME,
            data=[user_record],
            schema=self._get_schema()
        )
        logger.info("📋 Created users table in LanceDB")
        return table

    def _migrate_from_json(self):
        """Migrate existing users.json data to LanceDB (one-time)."""
        json_file = self.data_dir / "users.json"
        if not json_file.exists():
            return

        # Skip if table already has data (already migrated)
        table = self._get_table()
        if table is not None and len(table) > 0:
            logger.debug("LanceDB users table already has data, skipping JSON migration")
            return

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            users = data.get("users", {})
            if not users:
                return

            records = []
            for username, info in users.items():
                records.append({
                    "username": username,
                    "password_hash": info["password_hash"],
                    "salt": info["salt"],
                    "created_at": info.get("created_at", datetime.now().isoformat()),
                    "last_login": info.get("last_login") or "",
                })

            if records:
                if table is None:
                    self._create_table_with_user(records[0])
                    if len(records) > 1:
                        table = self._get_table()
                        table.add(records[1:])
                else:
                    table.add(records)

                logger.info(f"✅ Migrated {len(records)} user(s) from users.json to LanceDB")

                # Rename old file to prevent re-migration
                backup = json_file.with_suffix(".json.bak")
                json_file.rename(backup)
                logger.info("📁 Renamed users.json → users.json.bak")

        except Exception as e:
            logger.warning(f"JSON migration failed (non-critical): {e}")

    def _find_user(self, username: str) -> Optional[dict]:
        """Find a user by username."""
        table = self._get_table()
        if table is None:
            return None

        try:
            # Use pandas scan for reliable filtering on non-vector tables
            df = table.to_pandas()
            match = df[df["username"] == username]
            if not match.empty:
                return match.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"Error finding user '{username}': {e}")

        return None

    @staticmethod
    def _hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """
        Hash a password using PBKDF2-HMAC-SHA256.
        
        Args:
            password: Plain text password
            salt: Optional salt bytes (generated if not provided)
            
        Returns:
            Tuple of (hash_hex, salt_hex)
        """
        if salt is None:
            salt = secrets.token_bytes(32)

        pw_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations=100_000
        )
        return pw_hash.hex(), salt.hex()

    def has_users(self) -> bool:
        """Check if any users are registered."""
        table = self._get_table()
        if table is None:
            return False
        try:
            return len(table) > 0
        except Exception:
            return False

    def register(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Register a new user.
        
        Args:
            username: Desired username
            password: Plain text password (min 4 chars)
            
        Returns:
            Tuple of (success, message)
        """
        username = username.strip().lower()

        if not username:
            return False, "Username cannot be empty"
        if len(username) < 2:
            return False, "Username must be at least 2 characters"
        if len(password) < 4:
            return False, "Password must be at least 4 characters"

        if self._find_user(username) is not None:
            return False, "Username already exists"

        pw_hash, salt = self._hash_password(password)

        record = {
            "username": username,
            "password_hash": pw_hash,
            "salt": salt,
            "created_at": datetime.now().isoformat(),
            "last_login": "",
        }

        table = self._get_table()
        if table is None:
            self._create_table_with_user(record)
        else:
            table.add([record])

        logger.info(f"User '{username}' registered successfully (LanceDB)")
        return True, "Registration successful"

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Authenticate a user.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Tuple of (success, message)
        """
        username = username.strip().lower()

        user = self._find_user(username)
        if user is None:
            return False, "Invalid username or password"

        salt = bytes.fromhex(user["salt"])
        pw_hash, _ = self._hash_password(password, salt)

        if pw_hash != user["password_hash"]:
            return False, "Invalid username or password"

        # Update last login timestamp
        try:
            table = self._get_table()
            if table is not None:
                df = table.to_pandas()
                df.loc[df["username"] == username, "last_login"] = datetime.now().isoformat()
                self._db.drop_table(self.TABLE_NAME)
                self._db.create_table(self.TABLE_NAME, data=df.to_dict(orient="records"),
                                      schema=self._get_schema())
        except Exception as e:
            logger.warning(f"Could not update last_login: {e}")

        self._current_user = username
        self._is_locked = False
        logger.info(f"User '{username}' logged in successfully")
        return True, f"Welcome back, {username}!"

    def unlock(self, password: str) -> Tuple[bool, str]:
        """
        Unlock the session with password.
        
        Args:
            password: User's password
            
        Returns:
            Tuple of (success, message)
        """
        if not self._current_user:
            return False, "No active session"

        user = self._find_user(self._current_user)
        if user is None:
            return False, "User not found"

        salt = bytes.fromhex(user["salt"])
        pw_hash, _ = self._hash_password(password, salt)

        if pw_hash != user["password_hash"]:
            return False, "Incorrect password"

        self._is_locked = False
        logger.info(f"Session unlocked for '{self._current_user}'")
        return True, "Session unlocked"

    def lock(self):
        """Lock the current session."""
        self._is_locked = True
        logger.info(f"Session locked for '{self._current_user}'")

    def list_users(self) -> list:
        """
        List all registered users with safe (non-sensitive) fields.

        Returns:
            List of dicts with keys: username, created_at, last_login
        """
        table = self._get_table()
        if table is None:
            return []

        try:
            df = table.to_pandas()
            safe_cols = ['username', 'created_at', 'last_login']
            return df[safe_cols].to_dict(orient='records')
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []

    @property
    def is_locked(self) -> bool:
        return self._is_locked

    @property
    def current_user(self) -> Optional[str]:
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        return self._current_user is not None
