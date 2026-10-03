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

QWEN_IMAGE_MODERN_MODELS = {
    "qwen-image-3.0-pro",
    "qwen-image-3.0",
    "qwen-image-2.0-pro-2026-06-22",
    "qwen-image-2.0-pro-2026-04-22",
    "qwen-image-2.0",
    "qwen-image-2.0-2026-03-03",
    "qwen-image-2.0-pro",
    "qwen-image-2.0-pro-2026-03-03",
}

QWEN_IMAGE_LEGACY_SIZE_OPTIONS = {
    "1664*928",
    "1472*1104",
    "1328*1328",
    "1104*1472",
    "928*1664",
}


class QwenText2ImageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Tongyi Qwen text-to-image tool.
        """
        logger.info("Starting qwen text-to-image task")

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

            model = tool_parameters.get("model", "qwen-image-3.0-pro")
            negative_prompt = tool_parameters.get("negative_prompt", "")
            if negative_prompt:
                negative_prompt = negative_prompt[:500]
            prompt_extend = tool_parameters.get("prompt_extend")
            watermark = tool_parameters.get("watermark")
            size = tool_parameters.get("size", "")
            seed = tool_parameters.get("seed")
            n = tool_parameters.get("n")

            if not size and not model.startswith("qwen-image-3.0"):
                size = "2048*2048" if model in QWEN_IMAGE_MODERN_MODELS else "1664*928"

            if model in QWEN_IMAGE_MODERN_MODELS:
                if size and (not self._is_valid_qwen_image_2_size(size) or not 1 / 8 <= int(size.split("*")[0]) / int(size.split("*")[1]) <= 8):
                    msg = "❌ qwen-image-2.0系列的size总像素需在512*512到2048*2048之间"
                    logger.warning(msg)
                    yield self.create_text_message(msg)
                    return
            elif size not in QWEN_IMAGE_LEGACY_SIZE_OPTIONS:
                msg = "❌ 当前模型仅支持固定分辨率：1664*928/1472*1104/1328*1328/1104*1472/928*1664"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            yield self.create_text_message("🚀 文生图任务启动中...")
            yield self.create_text_message(f"🤖 使用模型: {model}")
            yield self.create_text_message(
                f"📝 提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
            )
            if size:
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
                "parameters": {},
            }

            if negative_prompt:
                payload["parameters"]["negative_prompt"] = negative_prompt.strip()
            if prompt_extend is not None:
                payload["parameters"]["prompt_extend"] = prompt_extend
            if model in {"qwen-image-3.0-pro", "qwen-image-3.0"}:
                mode = tool_parameters.get("prompt_extend_mode") or "direct"
                if mode not in {"direct", "agent"}:
                    yield self.create_text_message("❌ prompt_extend_mode 必须为 direct 或 agent")
                    return
                payload["parameters"]["prompt_extend_mode"] = mode
                if tool_parameters.get("enable_thinking") is not None:
                    payload["parameters"]["enable_thinking"] = bool(tool_parameters["enable_thinking"])
            if watermark is not None:
                payload["parameters"]["watermark"] = watermark
            if size:
                payload["parameters"]["size"] = size
            if n is not None:
                try:
                    n_value = int(n)
                except (TypeError, ValueError):
                    n_value = 1

                if model in QWEN_IMAGE_MODERN_MODELS:
                    if n_value < 1:
                        n_value = 1
                    if n_value > 6:
                        n_value = 6
                else:
                    n_value = 1
                payload["parameters"]["n"] = n_value
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
                    timeout=360,
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

            image_index = 0
            for choice in choices:
                for item in choice.get("message", {}).get("content", []):
                    if isinstance(item, dict) and item.get("image"):
                        image_index += 1
                        yield self.create_image_message(item["image"])
                        yield self.create_text_message(f"✅ 第 {image_index} 张图片生成完成！")
            if not image_index:
                yield self.create_text_message("❌ API 响应中未返回图像URL")
                return

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

            yield self.create_text_message("🎯 文生图任务完成！")
            logger.info("Qwen text-to-image task completed")

        except Exception as e:
            error_msg = f"❌ 生成图像时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _is_valid_qwen_image_2_size(size: str) -> bool:
        if not size or "*" not in size:
            return False
        try:
            width_text, height_text = size.split("*", 1)
            width = int(width_text)
            height = int(height_text)
        except (TypeError, ValueError):
            return False

        if width <= 0 or height <= 0:
            return False

        pixels = width * height
        return 512 * 512 <= pixels <= 2048 * 2048
