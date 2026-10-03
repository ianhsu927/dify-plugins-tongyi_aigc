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

WAN_27_MODELS = {"wan2.7-image-pro", "wan2.7-image"}
WAN_26_MODELS = {"wan2.6-t2i"}
SUPPORTED_MODELS = WAN_27_MODELS | WAN_26_MODELS

WAN_26_SIZE_OPTIONS = {
    "1280*1280",
    "1104*1472",
    "1472*1104",
    "960*1696",
    "1696*960",
}


class WanText2ImageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Tongyi Wanxiang text-to-image tool (sync for wan2.6 and wan2.7).
        """
        logger.info("Starting wan text-to-image task")

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

            model = tool_parameters.get("model", "wan2.7-image-pro")
            if model not in SUPPORTED_MODELS:
                msg = f"❌ 不支持的模型: {model}"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return
            is_wan27 = model in WAN_27_MODELS

            prompt = tool_parameters.get("prompt", "").strip()
            if not prompt:
                msg = "❌ 请输入提示词"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            prompt_limit = 5000 if is_wan27 else 2100
            if len(prompt) > prompt_limit:
                prompt = prompt[:prompt_limit]

            negative_prompt = tool_parameters.get("negative_prompt", "")
            if negative_prompt:
                negative_prompt = negative_prompt[:500]
            prompt_extend = tool_parameters.get("prompt_extend")
            watermark = tool_parameters.get("watermark")
            n = tool_parameters.get("n")
            size = tool_parameters.get("size", "2K" if is_wan27 else "1280*1280")
            seed = tool_parameters.get("seed")
            enable_sequential = tool_parameters.get("enable_sequential")
            thinking_mode = tool_parameters.get("thinking_mode")

            if not size:
                size = "2K" if is_wan27 else "1280*1280"

            if not self._is_valid_size(model=model, size=size, enable_sequential=bool(enable_sequential)):
                if is_wan27:
                    if bool(enable_sequential):
                        msg = "❌ wan2.7 组图模式仅支持 1K/2K，或总像素不超过 2048*2048 的宽*高"
                    else:
                        msg = "❌ wan2.7 文生图支持 1K/2K/4K，或符合范围的宽*高"
                else:
                    msg = "❌ wan2.6-t2i 总像素需在1280*1280至1440*1440之间，宽高比需在1:4至4:1之间"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            yield self.create_text_message("🚀 文生图任务启动中...")
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
                "parameters": {},
            }

            if not is_wan27:
                if negative_prompt:
                    payload["parameters"]["negative_prompt"] = negative_prompt
                if prompt_extend is not None:
                    payload["parameters"]["prompt_extend"] = prompt_extend
            elif enable_sequential is not None:
                payload["parameters"]["enable_sequential"] = bool(enable_sequential)

            if watermark is not None:
                payload["parameters"]["watermark"] = watermark

            if n is not None:
                try:
                    n_value = int(n)
                except (TypeError, ValueError):
                    n_value = None
                if n_value is not None:
                    if n_value < 1:
                        n_value = 1
                    if is_wan27 and payload["parameters"].get("enable_sequential"):
                        if n_value > 12:
                            n_value = 12
                    elif n_value > 4:
                        n_value = 4
                    payload["parameters"]["n"] = n_value

            payload["parameters"]["size"] = size

            if is_wan27 and thinking_mode is not None and not payload["parameters"].get("enable_sequential"):
                payload["parameters"]["thinking_mode"] = bool(thinking_mode)

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
                message = choice.get("message", {})
                content = message.get("content", [])
                for item in content:
                    if (
                        isinstance(item, dict)
                        and item.get("type") == "image"
                        and "image" in item
                    ):
                        image_index += 1
                        yield self.create_image_message(item["image"])
                        yield self.create_text_message(f"✅ 第 {image_index} 张图片生成完成！")

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
            logger.info("Wan text-to-image task completed")

        except Exception as e:
            error_msg = f"❌ 生成图像时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _is_valid_size(model: str, size: str, enable_sequential: bool) -> bool:
        if model in WAN_26_MODELS:
            return WanText2ImageTool._is_valid_custom_size(size, min_pixels=1280 * 1280, max_pixels=1440 * 1440) and 1 / 4 <= int(size.split("*")[0]) / int(size.split("*")[1]) <= 4

        if model == "wan2.7-image":
            if size in {"1K", "2K"}:
                return True
            return WanText2ImageTool._is_valid_custom_size(size, min_pixels=768 * 768, max_pixels=2048 * 2048)

        if model == "wan2.7-image-pro":
            if enable_sequential:
                if size in {"1K", "2K"}:
                    return True
                return WanText2ImageTool._is_valid_custom_size(size, min_pixels=768 * 768, max_pixels=2048 * 2048)

            if size in {"1K", "2K", "4K"}:
                return True
            return WanText2ImageTool._is_valid_custom_size(size, min_pixels=768 * 768, max_pixels=4096 * 4096)

        return False

    @staticmethod
    def _is_valid_custom_size(size: str, min_pixels: int, max_pixels: int) -> bool:
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

        ratio = width / height
        if ratio < 1 / 8 or ratio > 8:
            return False

        pixels = width * height
        return min_pixels <= pixels <= max_pixels
