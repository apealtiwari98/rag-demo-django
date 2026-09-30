import logging
import tempfile

from .base import *  # noqa: F403

DEBUG = False

# Services log expected failures (e.g. a failed index); keep test output clean.
logging.disable(logging.CRITICAL)

# Uploaded fixtures go to a throwaway directory, not the real media/ folder.
MEDIA_ROOT = tempfile.mkdtemp(prefix="documento-test-media-")

# Speed up user creation in tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Tests never touch a real embedding model or LLM: services are patched with
# langchain_core fakes sized to EMBEDDING_DIM (the pgvector column is fixed by
# the migration, so the dimension itself cannot be overridden here).
