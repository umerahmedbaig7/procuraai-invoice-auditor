"""ProcuraAI: LLM-assisted invoice and procurement compliance auditor (synthetic-data prototype)."""
__version__ = "0.1.0"

try:  # optional: read a local .env (git-ignored) without overriding variables already set in the shell
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:
    pass
