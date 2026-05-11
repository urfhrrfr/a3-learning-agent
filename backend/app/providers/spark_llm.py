from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlencode, urlparse

from websockets.exceptions import WebSocketException
from websockets.sync.client import connect

from .base import BaseLLMProvider, LLMProviderError


class SparkLLMProvider(BaseLLMProvider):
    """iFLYTEK Spark WebSocket provider."""

    name = "spark"

    def __init__(self) -> None:
        self.app_id = os.getenv("SPARK_APP_ID", "")
        self.api_key = os.getenv("SPARK_API_KEY", "")
        self.api_secret = os.getenv("SPARK_API_SECRET", "")
        self.model = os.getenv("SPARK_MODEL", "generalv3.5")
        self.endpoint = os.getenv("SPARK_API_URL", "wss://spark-api.xf-yun.com/v3.5/chat")
        self.timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

    def complete(self, prompt: str) -> str:
        if not (self.app_id and self.api_key and self.api_secret):
            raise LLMProviderError("SPARK_APP_ID, SPARK_API_KEY and SPARK_API_SECRET must be configured")

        request = {
            "header": {"app_id": self.app_id},
            "parameter": {"chat": {"domain": self.model, "temperature": 0.4, "max_tokens": 2048}},
            "payload": {
                "message": {
                    "text": [
                        {"role": "system", "content": "你是一个面向高校课程学习的教学资源生成助手。"},
                        {"role": "user", "content": prompt},
                    ]
                }
            },
        }

        chunks: list[str] = []
        try:
            with connect(
                self._signed_url(),
                open_timeout=self.timeout,
                close_timeout=self.timeout,
                ping_interval=None,
            ) as websocket:
                websocket.send(json.dumps(request, ensure_ascii=False))
                for message in websocket:
                    payload = json.loads(message)
                    header = payload.get("header", {})
                    code = header.get("code", 0)
                    if code != 0:
                        raise LLMProviderError(f"Spark provider returned code={code}: {header.get('message', payload)}")

                    choices = payload.get("payload", {}).get("choices", {})
                    for item in choices.get("text", []):
                        chunks.append(item.get("content", ""))

                    if choices.get("status") == 2:
                        break
        except LLMProviderError:
            raise
        except (OSError, TimeoutError, WebSocketException, json.JSONDecodeError) as exc:
            raise LLMProviderError(f"Spark provider request failed: {exc}") from exc

        content = "".join(chunks).strip()
        if not content:
            raise LLMProviderError("Spark provider returned empty content")
        return content

    def _signed_url(self) -> str:
        parsed = urlparse(self.endpoint)
        date = format_datetime(datetime.now(timezone.utc), usegmt=True)
        signature_origin = f"host: {parsed.netloc}\ndate: {date}\nGET {parsed.path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        return f"{self.endpoint}?{urlencode({'authorization': authorization, 'date': date, 'host': parsed.netloc})}"
