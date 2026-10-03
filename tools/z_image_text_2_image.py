from provider.endpoints import api_url as build_api_url
# author: sawyer-shi

import json
import logging
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)


class ZImageText2ImageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Z-Image text-to-image tool (sync).
        """
        logger.info("Starting z-image text-to-image task")

        try:
            api_key = self.runtime.credentials.get("api_key")
            if not api_key:
                msg = "❌ API密钥未配置"
                logger.error(msg)
                yield self.create_text_message(msg)
                return

            api_url = build_api_url(self.runtime.credentials, "/api/v1/services/aigc/multimodal-generation/generation")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            prompt = tool_parameters.get("prompt", "").strip()
            if not prompt:
                msg = "❌ 请输入提示词"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            if len(prompt) > 800:
                prompt = prompt[:800]

            model = tool_parameters.get("model", "z-image-turbo")
            prompt_extend = tool_parameters.get("prompt_extend")
            size = tool_parameters.get("size", "1024*1536")
            seed = tool_parameters.get("seed")

            if not size:
                size = "1024*1536"

            yield self.create_text_message("🚀 Z-Image 文生图任务启动中...")
            yield self.create_text_message(f"🤖 使用模型: {model}")
            yield self.create_text_message(
                f"📝 提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
            )
            yield self.create_text_message(f"📐 图像尺寸: {size}")
            yield self.create_text_message("⏳ 正在连接通义API...")

            payload: dict[str, Any] = {
                "model": model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"text": prompt},
                            ],
                        }
                    ]
                },
                "parameters": {
                    "size": size,
                },
            }

            if prompt_extend is not None:
                payload["parameters"]["prompt_extend"] = bool(prompt_extend)
            if seed is not None:
                try:
                    payload["parameters"]["seed"] = int(seed)
                except (TypeError, ValueError):
                    pass

            logger.info("Submitting request: %s", json.dumps(payload, ensure_ascii=False))
            yield self.create_text_message("🎨 正在生成图像，请稍候...")

            try:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=60,
                )
            except requests.exceptions.Timeout:
                msg = "❌ 请求超时，请稍后重试"
                logger.error(msg)
                yield self.create_text_message(msg)
                return
            except requests.exceptions.RequestException as e:
                msg = f"❌ 请求失败: {str(e)}"
                logger.error(msg)
                yield self.create_text_message(msg)
                return

            if response.status_code != 200:
                logger.error("API status %s: %s", response.status_code, response.text[:300])
                yield self.create_text_message(f"❌ API 响应状态码: {response.status_code}")
                if response.text:
                    yield self.create_text_message(f"🔧 响应内容: {response.text[:500]}")
                return

            try:
                resp_data = response.json()
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON: %s - %s", str(e), response.text[:300])
                yield self.create_text_message("❌ API 响应解析失败（非JSON）")
                return

            output = resp_data.get("output", {})
            choices = output.get("choices", [])
            if not choices:
                yield self.create_text_message("❌ API 响应中未返回图像数据")
                return

            yield self.create_text_message("🎉 图像生成成功！")

            for choice in choices:
                message = choice.get("message", {})
                content_items = message.get("content", [])
                for item in content_items:
                    if isinstance(item, dict) and "image" in item:
                        image_url = item.get("image", "").strip()
                        if image_url:
                            yield self.create_image_message(image_url)
                    if isinstance(item, dict) and "text" in item:
                        text_content = item.get("text", "").strip()
                        if text_content:
                            yield self.create_text_message(f"📝 改写提示词: {text_content}")

                reasoning_content = message.get("reasoning_content", "")
                if reasoning_content:
                    yield self.create_text_message(
                        f"🧠 思考过程: {reasoning_content.strip()}"
                    )

            usage = resp_data.get("usage", {})
            if usage:
                if isinstance(usage, dict):
                    yield self.create_text_message("📊 使用统计:")
                    for key, value in usage.items():
                        yield self.create_text_message(f"  - {key}: {value}")
                else:
                    try:
                        usage_text = json.dumps(usage, ensure_ascii=False)
                    except Exception:
                        usage_text = str(usage)
                    yield self.create_text_message(f"📊 使用信息: {usage_text}")

            yield self.create_text_message("🎯 Z-Image 文生图任务完成！")
            logger.info("Z-Image text-to-image task completed")

        except Exception as e:
            error_msg = f"❌ 生成图像时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)
