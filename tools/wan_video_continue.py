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


class WanVideoContinueTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Tongyi Wanxiang video continuation tool (async submit).
        """
        logger.info("Starting wan video continuation task")

        try:
            api_key = self.runtime.credentials.get("api_key")
            if not api_key:
                yield self.create_text_message("❌ API密钥未配置")
                return

            model = tool_parameters.get("model", "wan2.7-i2v").strip()
            if not model.startswith("wan2.7-i2v"):
                yield self.create_text_message("ℹ️ 视频续写仅支持 wan2.7-i2v，已自动回退为 wan2.7-i2v。")
                model = "wan2.7-i2v"

            api_url = build_api_url(self.runtime.credentials, "/api/v1/services/aigc/video-generation/video-synthesis")

            first_clip_input = self._pick_first_file(tool_parameters.get("first_clip_input"))
            first_clip_url = tool_parameters.get("first_clip_url", "")
            processed_first_clip = self._process_video(
                first_clip_input if first_clip_input else first_clip_url
            )
            if not processed_first_clip:
                yield self.create_text_message("❌ 请提供有效的首段视频（first_clip），支持 mp4/mov，时长建议 2-10 秒。")
                return

            last_frame_input = self._pick_first_file(tool_parameters.get("last_frame_input"))
            last_frame_url = tool_parameters.get("last_frame_url", "")
            processed_last_frame = self._process_image(
                last_frame_input if last_frame_input else last_frame_url
            )

            media: list[dict[str, str]] = [{"type": "first_clip", "url": processed_first_clip}]
            if processed_last_frame:
                media.append({"type": "last_frame", "url": processed_last_frame})

            payload: dict[str, Any] = {
                "model": model,
                "input": {
                    "media": media,
                },
                "parameters": {},
            }

            prompt = tool_parameters.get("prompt", "").strip()
            if prompt:
                payload["input"]["prompt"] = prompt[:5000]

            negative_prompt = tool_parameters.get("negative_prompt", "").strip()
            if negative_prompt:
                payload["input"]["negative_prompt"] = negative_prompt[:500]

            params = payload["parameters"]
            resolution = tool_parameters.get("resolution", "1080P").strip().upper()
            if resolution not in {"720P", "1080P"}:
                yield self.create_text_message("ℹ️ resolution 仅支持 720P/1080P，已自动回退为 1080P。")
                resolution = "1080P"
            params["resolution"] = resolution

            duration = tool_parameters.get("duration", 5)
            try:
                duration_value = int(duration)
            except (TypeError, ValueError):
                duration_value = 5
            if duration_value < 2:
                duration_value = 2
            if duration_value > 15:
                duration_value = 15
            params["duration"] = duration_value

            if tool_parameters.get("prompt_extend") is not None:
                params["prompt_extend"] = tool_parameters.get("prompt_extend")
            else:
                params["prompt_extend"] = True

            if tool_parameters.get("watermark") is not None:
                params["watermark"] = tool_parameters.get("watermark")
            else:
                params["watermark"] = False

            seed = tool_parameters.get("seed")
            if seed is not None and str(seed).strip() != "":
                try:
                    seed_value = int(seed)
                    if 0 <= seed_value <= 2147483647:
                        params["seed"] = seed_value
                    else:
                        yield self.create_text_message(
                            "ℹ️ seed 超出范围 [0, 2147483647]，已忽略该参数。"
                        )
                except (TypeError, ValueError):
                    yield self.create_text_message("ℹ️ seed 不是有效整数，已忽略该参数。")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }

            debug_payload = json.loads(json.dumps(payload))
            for media_item in debug_payload.get("input", {}).get("media", []):
                media_url = media_item.get("url", "")
                if isinstance(media_url, str) and len(media_url) > 200:
                    media_type = media_item.get("type", "media")
                    if media_type == "first_clip":
                        media_item["url"] = "data:video/...[Base64 Hidden]"
                    elif media_type == "last_frame":
                        media_item["url"] = "data:image/...[Base64 Hidden]"
                    else:
                        media_item["url"] = "...[Hidden]"
            logger.info("Request Payload: %s", json.dumps(debug_payload, ensure_ascii=False))

            yield self.create_text_message("🚀 视频续写任务启动中...")
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
                yield self.create_text_message("❌ 请求超时，请稍后重试")
                return
            except requests.exceptions.RequestException as e:
                yield self.create_text_message(f"❌ 请求失败: {str(e)}")
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
                yield self.create_text_message(self._format_success_message(result_data))
                yield self.create_json_message(result_data)
            else:
                yield self.create_text_message(f"❌ 响应格式异常: {response.text[:500]}")

            logger.info("Wan video continuation task submitted")

        except Exception as e:
            error_msg = f"❌ 视频续写时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _format_success_message(result_data: dict[str, Any]) -> str:
        task_id = result_data.get("output", {}).get("task_id", "unknown")
        task_status = result_data.get("output", {}).get("task_status", "unknown")
        return (
            f"🎬 视频续写任务已提交\nID: {task_id}\nStatus: {task_status}\n"
            "请使用 wan_video_query 查询结果。"
        )

    @staticmethod
    def _pick_first_file(file_value: Any) -> Any:
        if isinstance(file_value, list):
            if not file_value:
                return None
            return file_value[0]
        return file_value

    @staticmethod
    def _process_video(video_data: Any) -> str:
        if not video_data:
            return ""

        if isinstance(video_data, str):
            normalized = video_data.strip()
            if normalized.startswith(("http://", "https://", "oss://", "data:")):
                return normalized

        video_bytes = None
        if hasattr(video_data, "blob"):
            video_bytes = video_data.blob
        elif hasattr(video_data, "read") and callable(getattr(video_data, "read")):
            video_bytes = video_data.read()
            if isinstance(video_bytes, str):
                video_bytes = video_bytes.encode("utf-8")
        elif isinstance(video_data, bytes):
            video_bytes = video_data

        if not isinstance(video_bytes, bytes) or len(video_bytes) == 0:
            return ""
        if len(video_bytes) > 100 * 1024 * 1024:
            return ""

        try:
            b64_str = base64.b64encode(video_bytes).decode("utf-8")
            return f"data:video/mp4;base64,{b64_str}"
        except Exception:
            return ""

    @staticmethod
    def _process_image(image_data: Any) -> str:
        if not image_data:
            return ""

        if isinstance(image_data, str):
            normalized = image_data.strip()
            if normalized.startswith(("http://", "https://", "oss://", "data:")):
                return normalized

        image_bytes = None
        if hasattr(image_data, "blob"):
            image_bytes = image_data.blob
        elif hasattr(image_data, "read") and callable(getattr(image_data, "read")):
            image_bytes = image_data.read()
            if isinstance(image_bytes, str):
                image_bytes = image_bytes.encode("utf-8")
        elif isinstance(image_data, bytes):
            image_bytes = image_data

        if not isinstance(image_bytes, bytes) or len(image_bytes) == 0:
            return ""
        if len(image_bytes) > 20 * 1024 * 1024:
            return ""

        try:
            image = Image.open(BytesIO(image_bytes))
            ratio = image.width / image.height
            if image.width < 240 or image.width > 8000 or image.height < 240 or image.height > 8000:
                return ""
            if ratio < 1 / 8 or ratio > 8:
                return ""

            if image.mode in {"RGBA", "LA"} or (
                image.mode == "P" and "transparency" in image.info
            ):
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode != "RGBA":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[3])
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            output = BytesIO()
            image.save(output, format="JPEG", quality=95)
            encoded = base64.b64encode(output.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
        except Exception:
            return ""
