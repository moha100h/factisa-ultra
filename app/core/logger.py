import os, sys
from loguru import logger
os.makedirs("logs", exist_ok=True)
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> - <level>{message}</level>", level="INFO", colorize=True)
logger.add("logs/bot.log", rotation="10 MB", retention="7 days", level="DEBUG", encoding="utf-8")
