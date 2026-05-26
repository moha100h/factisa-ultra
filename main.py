import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from app.core.config import settings
from app.core.logger import logger
from app.db.engine import init_db
from app.middlewares.db import DbMiddleware
from app.middlewares.auth import AuthMiddleware
from app.handlers import start, clients, invoices, projects, workers, finance, reports


async def backup_scheduler(bot: Bot):
    from app.services.backup import create_backup, cleanup_backups
    while True:
        await asyncio.sleep(3600)
        fp = await create_backup()
        if fp:
            await cleanup_backups()
            logger.info(f"Auto backup: {fp}")


async def on_startup(bot: Bot):
    await init_db()
    asyncio.create_task(backup_scheduler(bot))
    logger.info(f"FacTisa Ultra v{settings.VERSION} started")
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"🟢 <b>FacTisa Ultra v{settings.VERSION}</b> راه‌اندازی شد!")
        except Exception:
            pass


async def on_shutdown(bot: Bot):
    logger.info("Bot shutting down...")


async def main():
    storage = RedisStorage.from_url(settings.REDIS_URL)
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)

    dp.message.middleware(DbMiddleware())
    dp.callback_query.middleware(DbMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    for router in [
        start.router, clients.router, invoices.router,
        projects.router, workers.router, finance.router, reports.router
    ]:
        dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
