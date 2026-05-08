"""LLM client abstractions."""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

from openai import OpenAI

from .config import load_json_config, auto_load_json_config
from .exceptions import LLMUnavailableError
from .prompts_loader import PromptRepository


class LLMClient(ABC):
    """Base interface for text generation."""

    @abstractmethod
    def complete(self, prompt: str | dict[str, str]) -> str:
        raise NotImplementedError


class APILLMClient(LLMClient):
    """LLM client implemented via the OpenAI SDK chat completions API."""

    def __init__(self,
                 config_name: str = "llm_config.json",
                 config_tag: str = "default",
                 config: dict | None = None):
        if config is None:
            config = auto_load_json_config(config_name, config_tag)
        self.base_url = config.get("base_url") or config.get("baseurl")
        self.api_key = config.get("api_key")
        self.model = config.get("model")
        self.payload_template = config.get("payload_template", {})
        self.call_count = 0
        if not self.base_url or not self.api_key:
            raise LLMUnavailableError("LLM base_url or API key missing")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def complete(self, prompt: str | dict[str, str], retry: int = 3, retry_delay: float = 2.0) -> str:
        self.call_count += 1
        request_overrides: dict = {}
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = []
            response_format = prompt.get("response_format")
            if response_format is not None:
                request_overrides["response_format"] = response_format
            max_tokens = prompt.get("max_tokens")
            if max_tokens is not None:
                try:
                    request_overrides["max_tokens"] = int(max_tokens)
                except (TypeError, ValueError):
                    pass
            if prompt.get("system"):
                messages.append({"role": "system", "content": prompt["system"]})
            if prompt.get("user"):
                messages.append({"role": "user", "content": prompt["user"]})

        last_exception = None
        for attempt in range(retry + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **{**self.payload_template, **request_overrides},
                )

                if not response.choices:
                    raise LLMUnavailableError("LLM provider returned no choices")
                message = response.choices[0].message
                if message is None:
                    raise LLMUnavailableError("LLM provider returned empty message")
                content = getattr(message, "content", None)
                if content is None and isinstance(message, dict):
                    content = message.get("content")
                if isinstance(content, list):
                    content = "".join(part.get("text", "") for part in content if isinstance(part, dict))

                return content or ""

            except Exception as exc:
                last_exception = exc
                if attempt < retry:
                    print(f"\n[Warning] LLM request failed (Attempt {attempt + 1}/{retry + 1}): {exc}")
                    print(f"Retrying in {retry_delay * (attempt + 1)}s...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue

        raise LLMUnavailableError(f"LLM provider error after {retry} retries: {last_exception}") from last_exception


def build_llm_client(config_name: str = "llm_config.json",
                     config_tag: str = "default") -> LLMClient:
    config = auto_load_json_config(config_name, config_tag)
    return APILLMClient(config=config)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE = REPO_ROOT / "examples" / "nonlin_div_term_1.c"


def _extract_loops_from_response(response: str) -> list[str]:
    """Parse the loop extraction JSON payload."""

    try:
        payload = json.loads(response)
        candidate = payload.get("loops") if isinstance(payload, dict) else payload
        if isinstance(candidate, list):
            return [str(item).strip() for item in candidate if str(item).strip()]
    except json.JSONDecodeError:
        pass
    matches = re.findall(r"for\s*\(.*?\)|while\s*\(.*?\)", response, flags=re.DOTALL)
    return [match.strip() for match in matches]


def _demo_completion(code_file: str | Path = DEFAULT_SAMPLE) -> None:
    """Manual smoke test for the configured LLM service."""

    code_path = Path(code_file)
    if not code_path.is_absolute():
        code_path = REPO_ROOT / code_path
    if not code_path.exists():
        raise FileNotFoundError(f"Sample code '{code_file}' does not exist at {code_path}")

    code = code_path.read_text(encoding="utf-8")
    prompt_repo = PromptRepository()
    client = build_llm_client()

    loop_prompt = prompt_repo.render("loop_extraction", code=code)
    loop_response = client.complete(loop_prompt)
    loops = _extract_loops_from_response(loop_response) or ["/* no loops detected */"]

    prediction_prompt = prompt_repo.render(
        "prediction",
        code=code,
        loops=json.dumps(loops, ensure_ascii=False, indent=2),
        references="[]",
    )
    prediction_response = client.complete(prediction_prompt)

    print(f"Loop extraction response for {code_path}:\n{loop_response}\n")
    print("Prediction response:\n", prediction_response)


if __name__ == "__main__":
    print(f"[LLM Demo] Using config/llm_config.json with sample {DEFAULT_SAMPLE}")
    try:
        _demo_completion()
    except LLMUnavailableError as exc:
        print(f"LLM test failed: {exc}")