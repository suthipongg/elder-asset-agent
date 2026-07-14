class ConversationMemory:
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self._history: list[dict[str, str]] = []
        self._tool_history: list[dict] = []

    def add_turn(self, user_msg: str, assistant_msg: str, tool_outputs: dict | None = None) -> None:
        self._history.append({"role": "user", "content": user_msg})
        self._history.append({"role": "assistant", "content": assistant_msg})
        self._tool_history.append(tool_outputs or {})
        self._enforce_window()

    def get_tool_history(self) -> dict:
        merged = {}
        for outputs in self._tool_history:
            if not outputs:
                continue
            for key, value in outputs.items():
                if not value:
                    continue
                
                # Portfolio can be dict or list, normalize to list for merging
                if key == "portfolio" and isinstance(value, dict):
                    value = [value]
                    
                if isinstance(value, list):
                    existing = merged.get(key, [])
                    if not isinstance(existing, list):
                        existing = [existing] if isinstance(existing, dict) else []
                        
                    # Auto-detect ID field for deduplication
                    id_field = next((k for k in ["account_id", "transaction_id", "case_id"] 
                                   if len(value) > 0 and isinstance(value[0], dict) and k in value[0]), None)
                    
                    if id_field:
                        existing_dict = {item[id_field]: item for item in existing if isinstance(item, dict) and id_field in item}
                        for item in value:
                            if isinstance(item, dict) and id_field in item:
                                existing_dict[item[id_field]] = item
                        merged[key] = list(existing_dict.values())
                    else:
                        merged[key] = value
                else:
                    merged[key] = value
                    
        # Limit transactions to 20 to avoid bloat
        if "transactions" in merged and isinstance(merged["transactions"], list):
            try:
                merged["transactions"].sort(key=lambda x: x.get("date", ""), reverse=True)
            except Exception:
                pass
            merged["transactions"] = merged["transactions"][:20]
            
        return merged

    def get_history(self) -> list[dict[str, str]]:
        return list(self._history)

    def _enforce_window(self) -> None:
        max_messages = self.max_turns * 2
        if len(self._history) > max_messages:
            self._history = self._history[-max_messages:]
        if len(self._tool_history) > self.max_turns:
            self._tool_history = self._tool_history[-self.max_turns:]

    def clear(self) -> None:
        self._history.clear()
        self._tool_history.clear()