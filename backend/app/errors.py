class AgentError(Exception):
    """Base class for all agent-facing errors — safe to show to users."""
    def __init__(self, user_message: str, internal_detail: str = None):
        self.user_message = user_message
        self.internal_detail = internal_detail or user_message
        super().__init__(self.user_message)


class DataLoadError(AgentError):
    """Raised when a data file/database can't be loaded."""
    pass


class AnalysisError(AgentError):
    """Raised when the agent can't produce an answer after all retries."""
    pass


class ChartError(AgentError):
    """Raised when chart generation fails — non-fatal, analysis result is still valid."""
    pass