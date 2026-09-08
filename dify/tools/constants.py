from pathlib import Path

import yaml

API_BASE_URL = "https://agent.tinyfish.ai"

# Top-level `version` is the plugin; `meta.version` is the manifest format.
_MANIFEST = Path(__file__).resolve().parents[1] / "manifest.yaml"


def _manifest_version() -> str:
    try:
        version = yaml.safe_load(_MANIFEST.read_text(encoding="utf-8")).get("version")
    except (OSError, yaml.YAMLError, AttributeError):
        version = None
    return str(version) if version else "0+unknown"


PLUGIN_VERSION = _manifest_version()
