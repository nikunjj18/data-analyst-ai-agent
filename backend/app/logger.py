import json
import logging
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Human-readable log file (for quick reading)
logging.basicConfig(
    filename=LOG_DIR / "agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("data_analyst_agent")

# Structured JSON log file (for programmatic analysis / eval later)
JSON_LOG_PATH = LOG_DIR / "agent_events.jsonl"


def log_event(event_type: str, **fields):
    """
    Logs a structured event to both the readable log and a JSON lines file.
    event_type examples: "question_received", "code_generated", "execution_success",
    "execution_failed", "self_correction_attempt", "chart_generated", "rate_limited"
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    entry = {"timestamp": timestamp, "event_type": event_type, **fields}

    # Human-readable line
    logger.info(f"{event_type} | {fields}")

    # Structured JSON line (one JSON object per line, easy to parse later)
    with open(JSON_LOG_PATH, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def log_error(event_type: str, error: Exception, **fields):
    log_event(event_type, error_type=type(error).__name__, error_message=str(error), **fields)