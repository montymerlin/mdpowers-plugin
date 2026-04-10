#!/usr/bin/env python3
"""Interactive setup wizard for the mdpowers transcribe skill.

Runs in local mode (Claude Code terminal, Cursor). For sandbox mode
(Cowork), the skill drives the same steps via chat UI — see
references/setup-sandbox.md.

SYNC NOTE: This file mirrors references/setup-sandbox.md.
Changes here must be reflected there.
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directories to path for lib imports
current_file = Path(__file__).resolve()
plugin_root = current_file.parent.parent.parent.parent
sys.path.insert(0, str(plugin_root / "lib"))

try:
    from host_mode import get_mdpowers_data_dir
except ImportError:
    print("ERROR: Could not import lib.host_mode. Ensure the mdpowers plugin structure is correct.")
    sys.exit(1)


def detect_environment() -> dict:
    """Detect local environment and return metadata.

    Returns:
        dict with keys:
            - os_name: 'Darwin', 'Linux', or 'Windows'
            - xdg_data_home: resolved Path to XDG data directory
            - cwd: current working directory Path
            - is_git_repo: bool
            - repo_name: str or None
            - master_exists: bool
            - master_path: Path to master vocabulary
            - existing_overlays: list of Path objects to existing overlays
    """
    import os
    import platform

    os_name = platform.system()
    if os_name == "Darwin":
        os_name = "Darwin"
    elif os_name == "Linux":
        os_name = "Linux"
    elif os_name == "Windows":
        os_name = "Windows"
    else:
        os_name = "Unknown"

    xdg_data_home = Path(get_mdpowers_data_dir())
    xdg_data_home.mkdir(parents=True, exist_ok=True)

    cwd = Path.cwd()

    # Check for git repo
    is_git_repo = (cwd / ".git").exists()
    repo_name = None
    if is_git_repo:
        git_config = cwd / ".git" / "config"
        if git_config.exists():
            try:
                content = git_config.read_text()
                for line in content.split("\n"):
                    if "url" in line and ".git" in line:
                        parts = line.split("/")
                        repo_name = parts[-1].replace(".git", "").strip()
                        break
            except Exception:
                pass
        if not repo_name:
            repo_name = cwd.name

    # Check for master vocabulary
    master_path = xdg_data_home / "vocabulary.json"
    master_exists = master_path.exists()

    # Scan for existing overlays
    existing_overlays = []
    mdpowers_dir = cwd / ".mdpowers"
    if mdpowers_dir.exists():
        existing_overlays = sorted(mdpowers_dir.glob("vocabulary.*.json"))

    return {
        "os_name": os_name,
        "xdg_data_home": xdg_data_home,
        "cwd": cwd,
        "is_git_repo": is_git_repo,
        "repo_name": repo_name,
        "master_exists": master_exists,
        "master_path": master_path,
        "existing_overlays": existing_overlays,
    }


def setup_master_vocabulary(detection: dict) -> Path:
    """Set up or update the master vocabulary file.

    Prompts user to:
    - Keep existing master, replace it, or import from file
    - Or create blank template if none exists

    Returns:
        Path to the master vocabulary file
    """
    master_path = detection["master_path"]

    print("\n" + "=" * 60)
    print("MASTER VOCABULARY SETUP")
    print("=" * 60)

    if master_path.exists():
        try:
            with open(master_path) as f:
                data = json.load(f)
                term_count = len([k for k in data.keys() if not k.startswith("_")])
        except Exception:
            term_count = 0

        print(f"\nMaster vocabulary found at:")
        print(f"  {master_path}")
        print(f"  ({term_count} terms)")
        print("\nOptions:")
        print("  [K]eep existing")
        print("  [R]eplace with blank template")
        print("  [I]mport from file")

        choice = input("\nChoose [K/R/I]: ").strip().upper()

        if choice == "K":
            print("✓ Keeping existing master vocabulary")
            return master_path
        elif choice == "R":
            _copy_template_to_path(master_path)
            print(f"✓ Master vocabulary replaced: {master_path}")
            return master_path
        elif choice == "I":
            import_path = Path(input("\nPath to vocabulary file to import: ").strip())
            if not import_path.exists():
                print(f"ERROR: File not found: {import_path}")
                return setup_master_vocabulary(detection)
            try:
                with open(import_path) as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print("ERROR: Invalid JSON in import file")
                return setup_master_vocabulary(detection)

            # Update metadata
            data["_meta"] = data.get("_meta", {})
            data["_meta"]["updated"] = datetime.utcnow().isoformat()

            master_path.parent.mkdir(parents=True, exist_ok=True)
            with open(master_path, "w") as f:
                json.dump(data, f, indent=2)

            print(f"✓ Master vocabulary imported: {master_path}")
            return master_path
        else:
            print("Invalid choice, try again.")
            return setup_master_vocabulary(detection)
    else:
        print("\nNo master vocabulary found.")
        print("Options:")
        print("  [B]lank template")
        print("  [I]mport from existing file")

        choice = input("\nChoose [B/I]: ").strip().upper()

        if choice == "B":
            _copy_template_to_path(master_path)
            print(f"✓ Blank master vocabulary created: {master_path}")
            return master_path
        elif choice == "I":
            import_path = Path(input("\nPath to vocabulary file: ").strip())
            if not import_path.exists():
                print(f"ERROR: File not found: {import_path}")
                return setup_master_vocabulary(detection)
            try:
                with open(import_path) as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print("ERROR: Invalid JSON")
                return setup_master_vocabulary(detection)

            data["_meta"] = data.get("_meta", {})
            data["_meta"]["updated"] = datetime.utcnow().isoformat()

            master_path.parent.mkdir(parents=True, exist_ok=True)
            with open(master_path, "w") as f:
                json.dump(data, f, indent=2)

            print(f"✓ Master vocabulary imported: {master_path}")
            return master_path
        else:
            print("Invalid choice, try again.")
            return setup_master_vocabulary(detection)


def setup_project_overlay(detection: dict) -> Path | None:
    """Set up project-local vocabulary overlay if in git repo.

    Returns:
        Path to overlay file, or None if skipped
    """
    if not detection["is_git_repo"]:
        print("\n(Not in a git repo, skipping project overlay)")
        return None

    print("\n" + "=" * 60)
    print("PROJECT-LOCAL OVERLAY SETUP")
    print("=" * 60)

    repo_name = detection["repo_name"] or "project"
    choice = input(f"\nCreate project overlay for '{repo_name}'? [y/n]: ").strip().lower()

    if choice != "y":
        print("Skipped project overlay")
        return None

    scope = input(f"\nScope name [{repo_name}]: ").strip() or repo_name

    mdpowers_dir = detection["cwd"] / ".mdpowers"
    mdpowers_dir.mkdir(exist_ok=True)

    overlay_path = mdpowers_dir / f"vocabulary.{scope}.json"

    # Create from template
    _copy_template_to_path(overlay_path, scope=scope)

    print(f"✓ Project overlay created: {overlay_path}")
    return overlay_path


def setup_gitignore(detection: dict) -> None:
    """Set up .gitignore to exclude .mdpowers/cache/ if in git repo."""
    if not detection["is_git_repo"]:
        print("\n(Not in a git repo, skipping .gitignore)")
        return

    print("\n" + "=" * 60)
    print("GITIGNORE SETUP")
    print("=" * 60)

    gitignore_path = detection["cwd"] / ".gitignore"
    cache_entry = ".mdpowers/cache/"

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if cache_entry in content:
            print(f"✓ .mdpowers/cache/ already in .gitignore")
            return

        # Append to existing
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n# mdpowers transcribe cache\n{cache_entry}\n"
        gitignore_path.write_text(content)
        print(f"✓ Added .mdpowers/cache/ to .gitignore")
    else:
        gitignore_path.write_text(f"# mdpowers transcribe cache\n{cache_entry}\n")
        print(f"✓ Created .gitignore with .mdpowers/cache/")


def check_env_vars() -> dict[str, bool]:
    """Check for required environment variables.

    Returns:
        dict with 'openai_api_key' and 'hf_token' bool status
    """
    import os

    print("\n" + "=" * 60)
    print("ENVIRONMENT VARIABLES")
    print("=" * 60)

    status = {}

    openai_key = os.getenv("OPENAI_API_KEY")
    status["openai_api_key"] = bool(openai_key)
    mark = "✓" if status["openai_api_key"] else "✗"
    print(f"\n{mark} OPENAI_API_KEY: {'set' if status['openai_api_key'] else 'NOT SET'}")
    if not status["openai_api_key"]:
        print("   → Get key at: https://platform.openai.com/account/api-keys")
        print("   → Export: export OPENAI_API_KEY='sk-...'")

    hf_token = os.getenv("HF_TOKEN")
    status["hf_token"] = bool(hf_token)
    mark = "✓" if status["hf_token"] else "✗"
    print(f"\n{mark} HF_TOKEN: {'set' if status['hf_token'] else 'NOT SET'}")
    if not status["hf_token"]:
        print("   → Get token at: https://huggingface.co/settings/tokens")
        print("   → Export: export HF_TOKEN='hf_...'")

    return status


def check_dependencies() -> dict[str, bool]:
    """Check for installed dependencies across all three paths.

    Returns:
        dict with tier status: 'path1_core', 'path2_heavy', 'nltk_data'
    """
    import subprocess

    print("\n" + "=" * 60)
    print("DEPENDENCIES")
    print("=" * 60)

    status = {}

    # Path 1: Core deps
    print("\n[Path 1 - Core]")
    try:
        import openai
        import soundfile
        status["path1_core"] = True
        print("✓ Core dependencies installed")
    except ImportError as e:
        status["path1_core"] = False
        print(f"✗ Missing: {e}")
        choice = input("Install Path 1 core deps? [y/n]: ").strip().lower()
        if choice == "y":
            subprocess.run(
                ["pip", "install", "-r", "requirements.txt"],
                cwd=Path(__file__).parent.parent,
                check=False
            )
            status["path1_core"] = True

    # Path 2: Heavy deps
    print("\n[Path 2 - WhisperX (~3GB)]")
    try:
        import whisperx
        status["path2_heavy"] = True
        print("✓ WhisperX installed")
    except ImportError:
        status["path2_heavy"] = False
        print("✗ WhisperX not installed")
        choice = input("Install Path 2 heavy deps? [y/n]: ").strip().lower()
        if choice == "y":
            script_path = Path(__file__).parent / "install_path2.sh"
            if script_path.exists():
                subprocess.run(["bash", str(script_path)], check=False)
                status["path2_heavy"] = True
            else:
                print(f"  (install script not found at {script_path})")

    # NLTK data
    print("\n[NLTK Data]")
    try:
        import nltk
        nltk.data.find("corpora/words")
        status["nltk_data"] = True
        print("✓ NLTK words corpus installed")
    except LookupError:
        status["nltk_data"] = False
        print("✗ NLTK words corpus not found")
        choice = input("Download NLTK words corpus? [y/n]: ").strip().lower()
        if choice == "y":
            script_path = Path(__file__).parent / "install_nltk_data.sh"
            if script_path.exists():
                subprocess.run(["bash", str(script_path)], check=False)
                status["nltk_data"] = True
            else:
                print(f"  (install script not found at {script_path})")

    return status


def print_completion_report(
    master_path: Path,
    overlay_path: Path | None,
    env_vars: dict[str, bool],
    deps: dict[str, bool],
) -> None:
    """Print formatted completion report."""
    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)

    print("\n[Files]")
    print(f"✓ Master vocabulary: {master_path}")
    if overlay_path:
        print(f"✓ Project overlay: {overlay_path}")
    else:
        print("  (no project overlay)")

    print("\n[Environment]")
    print(f"{'✓' if env_vars.get('openai_api_key') else '✗'} OPENAI_API_KEY")
    print(f"{'✓' if env_vars.get('hf_token') else '✗'} HF_TOKEN")

    print("\n[Dependencies]")
    print(f"{'✓' if deps.get('path1_core') else '✗'} Path 1 (Core)")
    print(f"{'✓' if deps.get('path2_heavy') else '✗'} Path 2 (WhisperX)")
    print(f"{'✓' if deps.get('nltk_data') else '✗'} NLTK Data")

    print("\n" + "=" * 60)
    print("Next steps:")
    print("  • Set missing environment variables (if any)")
    print("  • Install missing dependencies (if any)")
    print("  • Run: transcribe <audio-file>")
    print("=" * 60 + "\n")


def _copy_template_to_path(target_path: Path, scope: str | None = None) -> None:
    """Copy vocabulary template to target path.

    Args:
        target_path: where to write the vocabulary file
        scope: optional scope name for project overlays
    """
    template_path = Path(__file__).parent.parent / "assets" / "vocabulary.template.json"

    if template_path.exists():
        with open(template_path) as f:
            data = json.load(f)
    else:
        # Fallback: create minimal template
        data = {"_meta": {}}

    # Update metadata
    data["_meta"]["updated"] = datetime.utcnow().isoformat()
    if scope:
        data["_meta"]["scope"] = scope

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    """Run the interactive setup wizard."""
    print("\n" + "=" * 60)
    print("mdpowers transcribe — Setup Wizard")
    print("=" * 60)
    print("\nThis wizard will configure your transcription environment.")
    print("Press Ctrl+C at any time to cancel.\n")

    try:
        # Detect environment
        print("Detecting environment...")
        detection = detect_environment()
        print(f"✓ OS: {detection['os_name']}")
        print(f"✓ Data dir: {detection['xdg_data_home']}")
        print(f"✓ Working dir: {detection['cwd']}")
        if detection['is_git_repo']:
            print(f"✓ Git repo: {detection['repo_name']}")

        # Master vocabulary
        master_path = setup_master_vocabulary(detection)

        # Project overlay
        overlay_path = setup_project_overlay(detection)

        # .gitignore
        setup_gitignore(detection)

        # Environment variables
        env_vars = check_env_vars()

        # Dependencies
        deps = check_dependencies()

        # Final report
        print_completion_report(master_path, overlay_path, env_vars, deps)

    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
