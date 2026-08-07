class ConversationMemory:
    """Stores recent Q&A pairs so follow-up questions have context."""

    def __init__(self, max_history: int = 5):
        self.history = []
        self.max_history = max_history

    def add(self, question: str, result_summary: str):
        self.history.append({"question": question, "result": result_summary})
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def to_prompt_text(self) -> str:
        if not self.history:
            return "No previous questions in this conversation."
        lines = []
        for turn in self.history:
            lines.append(f"Q: {turn['question']}\nA: {turn['result']}")
        return "\n\n".join(lines)

    def clear(self):
        self.history = []