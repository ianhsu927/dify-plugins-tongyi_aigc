from provider.endpoints import api_url as build_api_url
# author: sawyer-shi

from typing import Any

import requests
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class TongyiAigcProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                raise ToolProviderCredentialValidationError("Tongyi API key is required")
            if len(api_key) < 10:
                raise ToolProviderCredentialValidationError("Tongyi API key length is invalid")
            self._test_tongyi_connection(api_key, credentials)
        except Exception as e:
            raise ToolProviderCredentialValidationError(
                f"Tongyi API credential validation failed: {str(e)}"
            )

    def _test_tongyi_connection(self, api_key: str, credentials: dict[str, Any]) -> None:
        url = build_api_url(credentials, "/compatible-mode/v1/chat/completions")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": "qwen-plus",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
            ],
            "max_tokens": 8,
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
        except requests.RequestException as req_err:
            raise ToolProviderCredentialValidationError(
                f"Unable to reach Tongyi service: {req_err}"
            )

        if response.status_code != 200:
            try:
                data = response.json()
                error_message = (
                    data.get("error", {}).get("message")
                    or data.get("message")
                    or response.text
                )
            except Exception:
                error_message = response.text
            raise ToolProviderCredentialValidationError(
                f"Tongyi API error {response.status_code}: {error_message}"
            )

        try:
            data = response.json()
        except ValueError:
            raise ToolProviderCredentialValidationError(
                "Tongyi API returned non-JSON response"
            )

        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            raise ToolProviderCredentialValidationError(
                "Tongyi API response missing valid choices"
            )
