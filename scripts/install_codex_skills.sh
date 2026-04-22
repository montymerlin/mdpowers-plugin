#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/montymerlin/mdpowers-plugin.git"
REF="main"
FROM_GITHUB=0
FORCE=0

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SKILLS_ROOT="${CODEX_HOME}/skills"
VENDOR_ROOT="${CODEX_HOME}/vendor_imports/repos/mdpowers-plugin"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Install mdpowers skills globally for Codex.

Usage:
  install_codex_skills.sh [--from-github] [--ref <git-ref>] [--force]
                          [--codex-home <path>] [--source-root <path>]

Modes:
  --from-github    Clone or update the repo at $CODEX_HOME/vendor_imports/repos/mdpowers-plugin
                   and install skills from there. This is the recommended auto-update flow.

  default          Install from the current checkout (or --source-root). Useful for local development.

Options:
  --force          Replace existing mdpowers Codex skill links if present.
  --codex-home     Override CODEX_HOME (default: ~/.codex).
  --source-root    Install from a specific checkout instead of the current repo.
  --ref            Git ref to clone/update when using --from-github (default: main).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from-github)
      FROM_GITHUB=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --codex-home)
      CODEX_HOME="$2"
      SKILLS_ROOT="${CODEX_HOME}/skills"
      VENDOR_ROOT="${CODEX_HOME}/vendor_imports/repos/mdpowers-plugin"
      shift 2
      ;;
    --source-root)
      SOURCE_ROOT="$2"
      shift 2
      ;;
    --ref)
      REF="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$FROM_GITHUB" -eq 1 ]]; then
  mkdir -p "$(dirname "$VENDOR_ROOT")"
  if [[ -d "${VENDOR_ROOT}/.git" ]]; then
    git -C "$VENDOR_ROOT" fetch --tags origin "$REF"
    git -C "$VENDOR_ROOT" checkout "$REF"
    git -C "$VENDOR_ROOT" pull --ff-only origin "$REF"
  else
    git clone --branch "$REF" "$REPO_URL" "$VENDOR_ROOT"
  fi
  SOURCE_ROOT="$VENDOR_ROOT"
fi

if [[ ! -f "${SOURCE_ROOT}/skills/clip/SKILL.md" ]]; then
  echo "Source root does not look like mdpowers-plugin: ${SOURCE_ROOT}" >&2
  exit 1
fi

mkdir -p "$SKILLS_ROOT"

declare -A SKILL_MAP=(
  ["mdpowers-clip"]="${SOURCE_ROOT}/skills/clip"
  ["mdpowers-convert"]="${SOURCE_ROOT}/skills/convert"
  ["mdpowers-transcribe"]="${SOURCE_ROOT}/skills/transcribe"
)

for skill_name in "${!SKILL_MAP[@]}"; do
  target="${SKILLS_ROOT}/${skill_name}"
  source="${SKILL_MAP[$skill_name]}"

  if [[ -e "$target" || -L "$target" ]]; then
    if [[ "$FORCE" -eq 1 ]]; then
      rm -rf "$target"
    else
      echo "Skill already exists: $target (use --force to replace)" >&2
      exit 1
    fi
  fi

  ln -s "$source" "$target"
done

cat <<EOF
Installed Codex skills:
  - mdpowers-clip
  - mdpowers-convert
  - mdpowers-transcribe

Skills root:  $SKILLS_ROOT
Source root:  $SOURCE_ROOT

If this is not the default Codex vendor path, export:
  export MDPOWERS_ROOT="$SOURCE_ROOT"

Restart Codex to pick up new skills.
EOF
