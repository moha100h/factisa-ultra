from typing import Callable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.db.engine import async_session

class DbMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: TelegramObject, data: Dict[str, Any]) -> Any:
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)
