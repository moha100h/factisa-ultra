import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
load_dotenv()

@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list = field(default_factory=list)
    DB_URL: str = os.getenv("DB_URL", "postgresql+asyncpg://ultra:ultra@db:5432/ultra")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "/backups")
    VERSION: str = "1.0.0"
    APP_NAME: str = "FacTisa Ultra"
    CURRENCY: str = "تومان"
    COMPANY_NAME: str = os.getenv("COMPANY_NAME", "")
    COMPANY_PHONE: str = os.getenv("COMPANY_PHONE", "")
    COMPANY_ADDRESS: str = os.getenv("COMPANY_ADDRESS", "")
    TAX_RATE: float = float(os.getenv("TAX_RATE", "9"))
    LOGO_PATH: str = os.getenv("LOGO_PATH", "/app/data/logo.png")

    def __post_init__(self):
        ids = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(i.strip()) for i in ids.split(",") if i.strip()]
        os.makedirs(os.path.dirname(self.LOGO_PATH), exist_ok=True)

    def is_admin(self, uid: int) -> bool:
        return uid in self.ADMIN_IDS

settings = Settings()
