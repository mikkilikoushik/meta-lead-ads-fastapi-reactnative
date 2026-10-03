import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name}. Copy .env.example to .env and fill it in."
        )
    return value


VERIFY_TOKEN = _required("META_VERIFY_TOKEN")
APP_SECRET = _required("META_APP_SECRET")
PAGE_ACCESS_TOKEN = _required("META_PAGE_ACCESS_TOKEN")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v23.0").strip()
DATABASE_PATH = os.getenv("DATABASE_PATH", "leads.db").strip()
