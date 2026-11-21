"""French prompts and fixed messages, one Markdown file per name and profile: `<profile>/<name>.md`.

Graph nodes are found by node name; `error` and `safety_footer` are read by the chat service.
"""

from pathlib import Path

from endorag_ingestion.core.settings import Profile

PROMPTS_DIR = Path(__file__).parent


def load_prompt(profile: Profile, node: str) -> str:
    """The prompt of `node` for `profile`. Raises `FileNotFoundError` when it does not exist."""
    path = PROMPTS_DIR / profile / f"{node}.md"
    if not path.is_file():
        raise FileNotFoundError(f"No prompt for node {node!r} in profile {profile!r}: {path}")
    return path.read_text(encoding="utf-8").strip()
