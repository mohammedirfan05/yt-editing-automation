# -*- coding: utf-8 -*-
"""
Centralized environment loader and API key resolution utility.
"""

import os
from typing import Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_env_file() -> None:
    """
    Auto-loads environment variables from root .env file if present into os.environ.
    """
    env_paths = [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    for path in env_paths:
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k and v and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass


def get_gemini_api_key(passed_key: Optional[str] = None) -> Optional[str]:
    """
    Resolves the Gemini API Key from explicit parameter or os.environ.
    Auto-loads .env if key is not yet present in environment.
    """
    if passed_key:
        return passed_key

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        load_env_file()
        key = os.environ.get("GEMINI_API_KEY")

    return key
