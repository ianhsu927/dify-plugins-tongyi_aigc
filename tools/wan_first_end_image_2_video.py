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


class WanFirstEndImage2VideoTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Tongyi Wanxiang first/last frame image-to-video tool (async submit).
        """
        logger.info("Starting wan first/last frame image-to-video task")

        try:
            model = tool_parameters.get("model", "wan2.2-kf2v-flash").strip()
            is_wan27_i2v = model.startswith("wan2.7-i2v")
            api_key = self.runtime.credentials.get("api_key")
            if not api_key:
                msg = "❌ API密钥未配置"
                logger.error(msg)
                yield self.create_text_message(msg)
                return

            first_frame_image = tool_parameters.get("first_frame_image")
            last_frame_image = tool_parameters.get("last_frame_image")
            template = tool_parameters.get("template", "").strip()
            audio_url = tool_parameters.get("audio_url", "").strip()

            if template and not last_frame_image:
                last_frame_image = first_frame_image

            if template:
                processed_first = self._process_image(first_frame_image)
                if not processed_first:
                    yield self.create_text_message("❌ 请提供首帧图片")
                    return
                processed_last = (
                    self._process_image(last_frame_image)
                    if last_frame_image
                    else processed_first
                )
            else:
                processed_first = self._process_image(first_frame_image)
                processed_last = self._process_image(last_frame_image)
                if not processed_first:
                    yield self.create_text_message("❌ 请提供首帧图片")
                    return
                if not processed_last:
                    yield self.create_text_message("❌ 请提供尾帧图片")
                    return

            prompt = tool_parameters.get("prompt", "").strip()
            if not is_wan27_i2v and not template and not prompt:
                yield self.create_text_message("❌ 非模板模式下必须提供提示词")
                return

            payload: dict[str, Any]
            if is_wan27_i2v:
                media: list[dict[str, str]] = [
                    {"type": "first_frame", "url": processed_first},
                    {"type": "last_frame", "url": processed_last},
                ]
                if audio_url:
                    media.append({"type": "driving_audio", "url": audio_url})

                payload = {
                    "model": model,
                    "input": {
                        "media": media,
                    },
                    "parameters": {},
                }
                if template:
                    yield self.create_text_message(
                        "ℹ️ wan2.7-i2v 不支持 template 参数，已忽略。"
                    )
                if prompt:
                    payload["input"]["prompt"] = prompt[:5000]
            else:
                payload = {
                    "model": model,
                    "input": {
                        "first_frame_url": processed_first,
                    },
                    "parameters": {},
                }

                if not template:
                    payload["input"]["last_frame_url"] = processed_last
                if template:
                    payload["input"]["template"] = template
                    payload["input"]["last_frame_url"] = processed_last
                if not template and prompt:
                    payload["input"]["prompt"] = prompt[:800]

            negative_prompt = tool_parameters.get("negative_prompt", "").strip()
            if negative_prompt:
                payload["input"]["negative_prompt"] = negative_prompt[:500]

            params = payload["parameters"]
            resolution = tool_parameters.get("resolution", "720P").strip().upper()
            if is_wan27_i2v and resolution and resolution not in {"720P", "1080P"}:
                yield self.create_text_message(
                    "ℹ️ wan2.7-i2v 仅支持 720P/1080P，已自动回退为 1080P。"
                )
                resolution = "1080P"
            if resolution:
                params["resolution"] = resolution
            params["duration"] = 5
            if tool_parameters.get("prompt_extend") is not None:
                params["prompt_extend"] = tool_parameters.get("prompt_extend")
            if tool_parameters.get("watermark") is not None:
                params["watermark"] = tool_parameters.get("watermark")
            if tool_parameters.get("seed") is not None:
                try:
                    params["seed"] = int(tool_parameters.get("seed"))
                except (TypeError, ValueError):
                    pass

            if is_wan27_i2v:
                api_url = build_api_url(self.runtime.credentials, "/api/v1/services/aigc/video-generation/video-synthesis")
            else:
                api_url = build_api_url(self.runtime.credentials, "/api/v1/services/aigc/image2video/video-synthesis")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }

            debug_payload = json.loads(json.dumps(payload))
            if "first_frame_url" in debug_payload.get("input", {}):
                if len(debug_payload["input"]["first_frame_url"]) > 200:
                    debug_payload["input"]["first_frame_url"] = "data:image/...[Base64 Hidden]"
            if "last_frame_url" in debug_payload.get("input", {}):
                if len(debug_payload["input"]["last_frame_url"]) > 200:
                    debug_payload["input"]["last_frame_url"] = "data:image/...[Base64 Hidden]"
            for media_item in debug_payload.get("input", {}).get("media", []):
                media_url = media_item.get("url", "")
                if isinstance(media_url, str) and len(media_url) > 200:
                    media_type = media_item.get("type", "media")
                    if media_type in {"first_frame", "last_frame"}:
                        media_item["url"] = "data:image/...[Base64 Hidden]"
                    elif media_type == "driving_audio":
                        media_item["url"] = "https://.../[Audio URL Hidden]"
                    else:
                        media_item["url"] = "...[Hidden]"
            logger.info("Request Payload: %s", json.dumps(debug_payload, ensure_ascii=False))

            yield self.create_text_message("🚀 首尾帧图生视频任务启动中...")
            yield self.create_text_message(f"🤖 使用模型: {model}")
            yield self.create_text_message("⏳ 正在连接通义API...")

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
                yield self.create_text_message(f"❌ API 响应状态码: {response.status_code}")
                if response.text:
                    yield self.create_text_message(f"🔧 响应内容: {response.text[:500]}")
                return

            try:
                result_data = response.json()
            except json.JSONDecodeError:
                yield self.create_text_message("❌ API 响应解析失败（非JSON）")
                return

            if "output" in result_data:
                yield self.create_text_message(
                    self._format_success_message(result_data, api_url)
                )
                yield self.create_json_message(result_data)
                logger.info("Wan first/last frame task submitted")
            else:
                yield self.create_text_message(
                    f"❌ 响应格式异常: {response.text[:500]}"
                )

        except Exception as e:
            error_msg = f"❌ 生成视频时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _process_image(image_data: Any) -> str:
        if not image_data:
            return ""

        if isinstance(image_data, str):
            image_data = image_data.strip()
            if image_data.startswith(("http://", "https://", "oss://", "data:")):
                return image_data

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
        elif isinstance(image_data, str):
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception:
                return ""
        else:
            return ""

        if not isinstance(image_bytes, bytes) or len(image_bytes) == 0:
            return ""
        if len(image_bytes) > 20 * 1024 * 1024:
            return ""

        try:
            image = Image.open(BytesIO(image_bytes))
            if image.width < 240 or image.width > 8000 or image.height < 240 or image.height > 8000:
                return ""
            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
            elif image.mode == "P":
                image = image.convert("RGB")
            elif image.mode != "RGB":
                image = image.convert("RGB")

            output_buffer = BytesIO()
            image.save(output_buffer, format="JPEG", quality=95)
            processed_bytes = output_buffer.getvalue()
            base64_string = base64.b64encode(processed_bytes).decode("utf-8")
            return f"data:image/jpeg;base64,{base64_string}"
        except Exception as e:
            logger.error("Error processing image: %s", str(e))
            return ""

    @staticmethod
    def _format_success_message(result_data: dict[str, Any], api_url: str) -> str:
        task_id = result_data.get("output", {}).get("task_id", "unknown")
        task_status = result_data.get("output", {}).get("task_status", "unknown")
        request_id = result_data.get("request_id", "unknown")
        response_text = f"""
🎬 首尾帧图生视频任务已提交！

📋 任务详情:
   • Task ID: {task_id}
   • Status: {task_status}
   • Request ID: {request_id}

💡 Next Steps:
   • Use the Video Query tool to check progress
   • Task ID: {task_id}
   • Status will update from 'PENDING' → 'RUNNING' → 'SUCCEEDED'/'FAILED'

📊 API Response Summary:
   • Endpoint: {api_url}
   • Method: POST
   • Status: Success (200)
   • Task Status: {task_status}
"""
        return response_text.strip()
