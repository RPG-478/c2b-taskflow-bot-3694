from __future__ import annotations
import os

# Discord Bot Token
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# Supabase Configuration
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# Flask Server Port for keep_alive.py
PORT: int = int(os.getenv("PORT", "8080"))
