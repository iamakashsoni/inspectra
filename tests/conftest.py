"""Shared pytest fixtures."""

import pytest

from inspectra.config.settings import InspectraSettings, LLMProvider


@pytest.fixture
def default_settings() -> InspectraSettings:
    return InspectraSettings(
        provider=LLMProvider.OLLAMA,
        model="qwen2.5-coder:14b",
        dry_run=True,
    )


SAMPLE_DIFF = """\
diff --git a/auth/service.py b/auth/service.py
index abc1234..def5678 100644
--- a/auth/service.py
+++ b/auth/service.py
@@ -40,7 +40,10 @@ class AuthService:
     def get_user(self, user_id: str):
-        query = f"SELECT * FROM users WHERE id = {user_id}"
+        query = "SELECT * FROM users WHERE id = %s"
+        return self.db.execute(query, (user_id,))
 
+    def login(self, username: str, password: str):
+        # TODO: add rate limiting
+        return self.db.query(f"SELECT * FROM users WHERE username='{username}'")
"""


@pytest.fixture
def sample_diff() -> str:
    return SAMPLE_DIFF
