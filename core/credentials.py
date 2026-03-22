"""
Credential lookup for login-required crawlers.
"""

import os
from typing import Dict, Optional


def get_login_kwargs(crawler_name: str) -> Optional[Dict[str, str]]:
    """Return login kwargs for a crawler, or None if credentials are not configured.

    Looks up LOGIN_USERNAME__<CRAWLER> and LOGIN_PASSWORD__<CRAWLER> env vars.
    Falls back to VJUDGE_USERNAME / VJUDGE_PASSWORD for backwards compatibility.
    """
    upper = crawler_name.upper()
    username = os.environ.get(f"LOGIN_USERNAME__{upper}")
    password = os.environ.get(f"LOGIN_PASSWORD__{upper}")
    # Backwards compat for VJudge
    if crawler_name == "vjudge" and not username:
        username = os.environ.get("VJUDGE_USERNAME")
        password = os.environ.get("VJUDGE_PASSWORD")
    if username and password:
        return {"login_user": username, "login_password": password}
    return None
