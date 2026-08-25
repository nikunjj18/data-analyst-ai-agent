import time
from google.genai.errors import ClientError
import httpx
from langsmith.run_helpers import get_current_run_tree

def call_with_retry(api_call_fn, max_retries=3, base_delay=15):
    """Retries an API call automatically on rate limits OR network timeouts."""
    for attempt in range(max_retries):
        try:
            return api_call_fn()
        except ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                wait_time = base_delay * (attempt + 1)
                print(f"Rate limit hit. Waiting {wait_time}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError) as e:
            wait_time = 5 * (attempt + 1)
            print(f"Network timeout. Retrying in {wait_time}s ({attempt + 1}/{max_retries})...")
            time.sleep(wait_time)

    raise RuntimeError("Exceeded max retries due to rate limiting or network issues.")

from langsmith.run_helpers import get_current_run_tree

def log_token_usage_to_trace(response):
    """Attaches Gemini's real token usage to the current LangSmith trace, since
    automatic extraction only works with deep LangChain integration, not the
    raw SDK."""
    try:
        usage = response.usage_metadata
        run = get_current_run_tree()
        if run:
            run.metadata["input_tokens"] = usage.prompt_token_count
            run.metadata["output_tokens"] = usage.candidates_token_count
            run.metadata["total_tokens"] = usage.total_token_count
    except Exception:
        pass