"""Host mode detection and path translation for the transcribe skill.

The skill runs in two host modes:
- 'local': full local terminal hosts such as Claude Code, Codex, or Cursor
  with direct subprocess invocation, real filesystem, and real GPU/MPS access.
- 'sandbox': constrained skill hosts such as Cowork with a sandboxed mount,
  no GPU, and session timeouts. Path 2 requires script emission instead of
  direct invocation.

Detection uses environment heuristics with an explicit override via
$MDPOWERS_HOST_MODE.
"""

import os
import platform
from pathlib import Path
from typing import Optional

from .errors import HostModeError


# ---------------------------------------------------------------------------
# Host mode detection
# ---------------------------------------------------------------------------

def detect_host_mode() -> str:
    """Detect whether we're running in a local terminal or a sandbox.

    Priority:
    1. $MDPOWERS_HOST_MODE env var (explicit override: 'local' or 'sandbox')
    2. /sessions/ path heuristic (sandboxed host such as Cowork)
    3. $CLAUDECODE env var (Claude Code terminal)
    4. $CURSOR_AGENT or $TERM_PROGRAM=cursor (Cursor)
    5. Default: 'local' (the common case)

    Returns:
        'local' or 'sandbox'
    """
    explicit = os.environ.get("MDPOWERS_HOST_MODE", "").strip().lower()
    if explicit in ("local", "sandbox"):
        return explicit

    # Sandboxed-host heuristic: working dir is under /sessions/
    cwd = os.getcwd()
    if os.path.exists("/sessions") and "/sessions/" in cwd:
        return "sandbox"

    # Claude Code terminal
    if os.environ.get("CLAUDECODE") == "1":
        return "local"

    # Cursor agent
    if os.environ.get("CURSOR_AGENT") or os.environ.get("TERM_PROGRAM") == "cursor":
        return "local"

    return "local"


def is_sandbox() -> bool:
    """Convenience: True if running in sandbox mode."""
    return detect_host_mode() == "sandbox"


# ---------------------------------------------------------------------------
# Workspace root discovery
# ---------------------------------------------------------------------------

def find_workspace_root(cwd: Optional[Path] = None) -> Path:
    """Walk up from cwd looking for .mdpowers/ or .git/ directory.

    Returns the directory containing the first marker found,
    or cwd itself if no marker is found before reaching the filesystem root.
    """
    current = Path(cwd) if cwd else Path.cwd()
    current = current.resolve()

    for parent in [current, *current.parents]:
        if (parent / ".mdpowers").is_dir() or (parent / ".git").is_dir():
            return parent
    return current


# ---------------------------------------------------------------------------
# Host path persistence (sandbox mode)
# ---------------------------------------------------------------------------

_HOST_PATH_FILE = ".mdpowers/host-path"


def load_host_path(workspace_root: Path) -> Optional[str]:
    """Read the stored host-local path from .mdpowers/host-path.

    This file is written during `/transcribe setup` in sandbox mode.
    It maps the sandbox mount to the user's real filesystem path so
    emitted run scripts contain correct local paths.

    Returns:
        The host-local path string, or None if the file doesn't exist.
    """
    host_path_file = workspace_root / _HOST_PATH_FILE
    if host_path_file.is_file():
        content = host_path_file.read_text().strip()
        if content:
            return content
    return None


def save_host_path(workspace_root: Path, host_path: str) -> None:
    """Persist the user-local host path for script emission.

    Args:
        workspace_root: The workspace root in the current environment.
        host_path: The user's real filesystem path (e.g. /Users/name/...).
    """
    mdpowers_dir = workspace_root / ".mdpowers"
    mdpowers_dir.mkdir(parents=True, exist_ok=True)
    (mdpowers_dir / "host-path").write_text(host_path.rstrip("/") + "\n")


# ---------------------------------------------------------------------------
# Path translation (sandbox <-> host)
# ---------------------------------------------------------------------------

def translate_sandbox_to_host(
    sandbox_path: str,
    mount_root: str,
    host_root: str,
) -> str:
    """Swap a sandbox mount prefix for the host-local prefix.

    Example:
        translate_sandbox_to_host(
            '/sessions/abc/mnt/myrepo/transcripts/out.md',
            '/sessions/abc/mnt/myrepo',
            '/Users/name/Documents/myrepo'
        )
        -> '/Users/name/Documents/myrepo/transcripts/out.md'

    Raises:
        HostModeError: If sandbox_path doesn't start with mount_root.
    """
    mount_root = mount_root.rstrip("/")
    host_root = host_root.rstrip("/")

    if not sandbox_path.startswith(mount_root):
        raise HostModeError(
            f"Path '{sandbox_path}' is not under the expected mount root "
            f"'{mount_root}'. Cannot translate to host path."
        )

    relative = sandbox_path[len(mount_root):]
    return host_root + relative


def translate_host_to_sandbox(
    host_path: str,
    host_root: str,
    mount_root: str,
) -> str:
    """Swap a host-local prefix for the sandbox mount prefix.

    Inverse of translate_sandbox_to_host.
    """
    host_root = host_root.rstrip("/")
    mount_root = mount_root.rstrip("/")

    if not host_path.startswith(host_root):
        raise HostModeError(
            f"Path '{host_path}' is not under the expected host root "
            f"'{host_root}'. Cannot translate to sandbox path."
        )

    relative = host_path[len(host_root):]
    return mount_root + relative


# ---------------------------------------------------------------------------
# XDG helpers
# ---------------------------------------------------------------------------

def get_xdg_data_home() -> Path:
    """Return the XDG_DATA_HOME path, respecting platform defaults.

    - Explicit $XDG_DATA_HOME if set
    - macOS: ~/Library/Application Support
    - Linux/other: ~/.local/share
    - Windows: %LOCALAPPDATA% or ~/.local/share fallback
    """
    explicit = os.environ.get("XDG_DATA_HOME")
    if explicit:
        return Path(explicit)

    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        return home / "Library" / "Application Support"
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data)
        return home / ".local" / "share"
    else:
        return home / ".local" / "share"


def get_mdpowers_data_dir() -> Path:
    """Return the mdpowers data directory under XDG_DATA_HOME.

    This is where the global master vocabulary lives:
        $XDG_DATA_HOME/mdpowers/vocabulary.json
    """
    return get_xdg_data_home() / "mdpowers"
