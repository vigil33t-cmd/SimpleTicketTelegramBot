from pydantic_settings import BaseSettings


class Config(BaseSettings):
    BOT_TOKEN: str = "token"
    MONGO_URI: str = "mongodb://user:password@ip:port/"
    MONGO_DB_NAME: str = "tickets"
    GROUP_CHAT_ID: int = 0  # chatid


config = Config()
