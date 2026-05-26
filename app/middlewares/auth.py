from typing import Callable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.core.config import settings

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: TelegramObject, data: Dict[str, Any]) -> Any:
        user = data.get("event_from_user")
        data["is_admin"] = settings.is_admin(user.id) if user else False
        return await handler(event, data)
