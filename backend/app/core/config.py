from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass(frozen=True)
class Settings:
    supabase_url: str = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_base_url: str = os.getenv(
        "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
    ).rstrip("/")
    nvidia_model: str = os.getenv("NVIDIA_MODEL", "")
    nvidia_timeout_seconds: float = float(os.getenv("NVIDIA_TIMEOUT_SECONDS", "45"))
    vosk_model_path: str = os.getenv("VOSK_MODEL_PATH", "")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

    @property
    def supabase_configured(self) -> bool:
        endpoint = urlsplit(self.supabase_url)
        return bool(
            endpoint.scheme in {"https", "http"}
            and endpoint.hostname
            and "YOUR-" not in self.supabase_url
            and "YOUR_" not in self.supabase_anon_key
            and self.supabase_anon_key
        )

    @property
    def nvidia_configured(self) -> bool:
        return bool(self.nvidia_api_key and self.nvidia_model)


settings = Settings()
