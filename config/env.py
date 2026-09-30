from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
# Values already present in the process environment win over .env.
env.read_env(BASE_DIR / ".env")
