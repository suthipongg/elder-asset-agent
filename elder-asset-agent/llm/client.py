class LLMClient:
    def generate(self, messages: list[dict]) -> str:
        """
        Returns a model-generated string.
        Implementation may call any LLM or be mocked.
        """
        raise NotImplementedError
