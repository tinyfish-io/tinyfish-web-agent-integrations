from pathlib import Path

API_BASE_URL = "https://agent.tinyfish.ai"

_MANIFEST = Path(__file__).resolve().parents[1] / "manifest.yaml"


def _manifest_version() -> str:
    try:
        for line in _MANIFEST.read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                return line.split(":", 1)[1].split("#", 1)[0].strip().strip("'\"")
    except OSError:
        pass
    return "0+unknown"


PLUGIN_VERSION = _manifest_version()
