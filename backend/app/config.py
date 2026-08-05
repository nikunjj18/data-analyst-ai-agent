import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    @classmethod
    def validate(cls):
        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is missing. Check your .env file."
            )

config = Config()
config.validate()