from provider.endpoints import api_url as build_api_url
# author: sawyer-shi

import base64
import json
import logging
from collections.abc import Generator
from io import BytesIO
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from PIL import Image

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

QWEN_IMAGE_EDIT_MAX_PLUS_MODELS = {
    "qwen-image-edit-max",
    "qwen-image-edit-max-2026-01-16",
    "qwen-image-edit-plus",
    "qwen-image-edit-plus-2025-12-15",
    "qwen-image-edit-plus-2025-10-30",
}


class QwenImage2ImageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Tongyi Qwen image-to-image tool.
        """
        logger.info("Starting qwen image-to-image task")

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

            images = tool_parameters.get("images", [])
            if not images or not isinstance(images, list):
                msg = "❌ 请提供参考图像"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return
            if len(images) > 3:
                msg = "❌ 最多支持3张参考图片"
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

            if size and not self._is_size_valid_for_model(model, size):
                if model in QWEN_IMAGE_MODERN_MODELS:
                    msg = "❌ qwen-image-2.0系列size总像素需在512*512到2048*2048之间"
                elif model in QWEN_IMAGE_EDIT_MAX_PLUS_MODELS:
                    msg = "❌ qwen-image-edit-max/plus系列size宽高均需在512到2048之间"
                else:
                    msg = "❌ qwen-image-edit模型不支持size参数"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            yield self.create_text_message("🚀 图生图任务启动中...")
            yield self.create_text_message(f"🤖 使用模型: {model}")
            yield self.create_text_message(
                f"📝 提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
            )
            yield self.create_text_message(f"📷 参考图片数量: {len(images)}")
            yield self.create_text_message("⏳ 正在处理输入图像文件...")

            processed_images: list[str] = []
            for i, image_data in enumerate(images):
                processed_image = self._process_image(image_data)
                if not processed_image:
                    msg = f"❌ 第 {i + 1} 张图像处理失败"
                    logger.warning(msg)
                    yield self.create_text_message(msg)
                    return
                processed_images.append(processed_image)

            content = [{"image": img} for img in processed_images] + [{"text": prompt}]

            payload: dict[str, Any] = {
                "model": model,
                "input": {"messages": [{"role": "user", "content": content}]},
                "parameters": {},
            }

            if n is not None:
                try:
                    n_value = int(n)
                except (TypeError, ValueError):
                    n_value = None

                if n_value is not None:
                    if model == "qwen-image-edit":
                        n_value = 1
                    else:
                        if n_value < 1:
                            n_value = 1
                        if n_value > 6:
                            n_value = 6
                    payload["parameters"]["n"] = n_value
            if negative_prompt:
                payload["parameters"]["negative_prompt"] = negative_prompt
            if size and model != "qwen-image-edit":
                payload["parameters"]["size"] = size
            if prompt_extend is not None and model != "qwen-image-edit":
                payload["parameters"]["prompt_extend"] = bool(prompt_extend)
            if model in {"qwen-image-3.0-pro", "qwen-image-3.0"}:
                mode = tool_parameters.get("prompt_extend_mode") or "direct"
                if mode not in {"direct", "agent"}:
                    yield self.create_text_message("❌ prompt_extend_mode 必须为 direct 或 agent")
                    return
                if mode == "agent":
                    yield self.create_text_message("❌ 图生图仅支持 direct 提示词改写")
                    return
                payload["parameters"]["prompt_extend_mode"] = mode
                if tool_parameters.get("enable_thinking") is not None:
                    payload["parameters"]["enable_thinking"] = bool(tool_parameters["enable_thinking"])
            if watermark is not None:
                payload["parameters"]["watermark"] = bool(watermark)
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
                content_items = message.get("content", [])
                for item in content_items:
                    if isinstance(item, dict) and "image" in item:
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

            yield self.create_text_message("🎯 图生图任务完成！")
            logger.info("Qwen image-to-image task completed")

        except Exception as e:
            error_msg = f"❌ 生成图像时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _process_image(image_data: Any) -> str:
        if not image_data:
            return ""

        if hasattr(image_data, "blob"):
            image_bytes = image_data.blob
        elif hasattr(image_data, "read") and callable(getattr(image_data, "read")):
            image_bytes = image_data.read()
            if isinstance(image_bytes, str):
                image_bytes = image_bytes.encode("utf-8")
        elif isinstance(image_data, bytes):
            image_bytes = image_data
        elif isinstance(image_data, str) and image_data.startswith("data:"):
            try:
                _, base64_data = image_data.split(",", 1)
                image_bytes = base64.b64decode(base64_data)
            except Exception:
                return ""
        elif isinstance(image_data, str) and image_data.startswith(("http://", "https://")):
            return image_data
        elif isinstance(image_data, str) and len(image_data) < 1000:
            try:
                with open(image_data, "rb") as image_file:
                    image_bytes = image_file.read()
            except Exception:
                return ""
        elif isinstance(image_data, str):
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception:
                return ""
        else:
            return ""

        if not isinstance(image_bytes, bytes) or len(image_bytes) == 0:
            return ""

        if len(image_bytes) > 10 * 1024 * 1024:
            return ""

        try:
            image = Image.open(BytesIO(image_bytes))

            if image.width < 384 or image.height < 384:
                return ""
            if image.width > 3072 or image.height > 3072:
                return ""

            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
            elif image.mode == "P":
                image = image.convert("RGB")

            output_buffer = BytesIO()
            image.save(output_buffer, format="PNG", optimize=True)
            processed_bytes = output_buffer.getvalue()

            base64_string = base64.b64encode(processed_bytes).decode("utf-8")
            return f"data:image/png;base64,{base64_string}"
        except Exception as e:
            logger.error("Error processing image: %s", str(e))
            return ""

    @staticmethod
    def _is_size_valid_for_model(model: str, size: str) -> bool:
        if not size:
            return True

        if "*" not in size:
            return False

        try:
            width_text, height_text = size.split("*", 1)
            width = int(width_text)
            height = int(height_text)
        except (TypeError, ValueError):
            return False

        if width <= 0 or height <= 0:
            return False

        if model in QWEN_IMAGE_MODERN_MODELS:
            pixels = width * height
            return 512 * 512 <= pixels <= 2048 * 2048 and 1 / 8 <= width / height <= 8

        if model in QWEN_IMAGE_EDIT_MAX_PLUS_MODELS:
            return 512 <= width <= 2048 and 512 <= height <= 2048

        return model != "qwen-image-edit"
