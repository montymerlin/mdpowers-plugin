"""Exception hierarchy for the mdpowers transcribe skill.

All skill-specific exceptions inherit from TranscribeError, allowing
callers to catch broadly or narrowly as needed. Runners catch at the
top level; lib modules raise specific subclasses.
"""


class TranscribeError(Exception):
    """Base exception for all transcribe skill errors."""


class ProbeError(TranscribeError):
    """Raised when source or environment probing fails.

    Examples: YouTube URL returns 404, yt-dlp not found, ffprobe
    can't read a local file, unsupported source type.
    """


class VocabularyError(TranscribeError):
    """Raised for vocabulary loading, validation, or promotion failures.

    Examples: malformed vocab JSON, missing required _meta key,
    promotion conflict that needs user resolution.
    """

    def __init__(self, message: str, conflict_payload: dict | None = None):
        super().__init__(message)
        self.conflict_payload = conflict_payload


class SpeakerError(TranscribeError):
    """Raised when speaker identification encounters an unrecoverable issue.

    Examples: metadata research returns invalid JSON, LLM guess
    returns names exceeding the diarized speaker count.
    """


class DiarizationError(TranscribeError):
    """Raised when diarization or alignment fails.

    Examples: pyannote model not downloaded, HF_TOKEN rejected,
    OOM during alignment (after retry exhaustion).
    """


class HostModeError(TranscribeError):
    """Raised for host-mode detection or path translation failures.

    Examples: sandbox mode with no .mdpowers/host-path file configured,
    path translation produces a non-existent host path.
    """


class PathwayError(TranscribeError):
    """Raised when a pathway cannot execute.

    Examples: user requested --pathway local but whisperx not installed,
    Path 3 stub invoked in v0.1, pathway preconditions not met.
    """
