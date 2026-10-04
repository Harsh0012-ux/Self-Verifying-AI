from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import OpenAI
from app.config import settings

@dataclass(frozen=True)
class Generation: code: str; token_usage: int | None
class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> Generation: ...
class OpenAIClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        client_options = {"api_key": api_key or settings.llm_api_key}
        if settings.llm_base_url is not None:
            client_options["base_url"] = settings.llm_base_url
        self.client = OpenAI(**client_options); self.model = model or settings.llm_model
    def generate(self, prompt: str) -> Generation:
        if not settings.llm_api_key: raise RuntimeError("LLM_API_KEY is required")
        response = self.client.responses.create(model=self.model, input=prompt)
        return Generation(response.output_text, getattr(response.usage, "total_tokens", None))
