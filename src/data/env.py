import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    rgb_dir: Path | None
    allbands_dir: Path | None
    app_mode: str
    artifacts_dir: Path
    seed: int


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    rgb_dir = os.getenv("EUROSAT_RGB_DIR")
    allbands_dir = os.getenv("EUROSAT_ALLBANDS_DIR")
    artifacts_dir = os.getenv("ARTIFACTS_DIR") or "artifacts"

    return Settings(
        rgb_dir=PROJECT_ROOT / Path(rgb_dir).expanduser() if rgb_dir else None,
        allbands_dir=PROJECT_ROOT / Path(allbands_dir).expanduser() if allbands_dir else None,
        app_mode=os.getenv("APP_MODE") or "dev",
        artifacts_dir=PROJECT_ROOT / Path(artifacts_dir).expanduser(),
        seed=int(os.getenv("SEED") or "42"),
    )
