class ConversationMemory:
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self._history: list[dict[str, str]] = []

    def add_turn(self, user_msg: str, assistant_msg: str) -> None:
        self._history.append({"role": "user", "content": user_msg})
        self._history.append({"role": "assistant", "content": assistant_msg})
        self._enforce_window()

    def add_user_message(self, user_msg: str) -> None:
        self._history.append({"role": "user", "content": user_msg})
        self._enforce_window()

    def add_assistant_message(self, assistant_msg: str) -> None:
        self._history.append({"role": "assistant", "content": assistant_msg})
        self._enforce_window()

    def get_history(self) -> list[dict[str, str]]:
        return list(self._history)

    def _enforce_window(self) -> None:
        max_messages = self.max_turns * 2
        if len(self._history) > max_messages:
            self._history = self._history[-max_messages:]

    def clear(self) -> None:
        self._history.clear()
