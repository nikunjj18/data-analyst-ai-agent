import os
from dotenv import load_dotenv
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGSMITH_TRACING", "false")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "data-analyst-agent")

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "data-analyst-agent")
    LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false")

    @classmethod
    def validate(cls):
        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is missing. Check your .env file."
            )

config = Config()
config.validate()