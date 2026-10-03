from provider.endpoints import api_url as build_api_url
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


class HappyHorseReferenceVideoTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        HappyHorse reference-image-to-video tool (async submit).
        """
        logger.info("Starting HappyHorse reference-image-to-video task")

        try:
            api_key = self.runtime.credentials.get("api_key")
            if not api_key:
                msg = "❌ API密钥未配置"
                logger.error(msg)
                yield self.create_text_message(msg)
                return

            api_url = build_api_url(self.runtime.credentials, "/api/v1/services/aigc/video-generation/video-synthesis")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }

            model = str(tool_parameters.get("model") or "happyhorse-1.1-r2v").strip()
            
            # Process reference images
            media: list[dict[str, str]] = []
            files = tool_parameters.get("files")
            if files:
                if isinstance(files, list):
                    file_list = files
                else:
                    file_list = [files]
                for file_obj in file_list:
                    try:
                        processed_img = self._process_image(file_obj)
                        if processed_img:
                            media.append({"type": "reference_image", "url": processed_img})
                    except ValueError as e:
                        msg = f"❌ 参考图片处理失败: {str(e)}"
                        logger.error(msg)
                        yield self.create_text_message(msg)
                        return
            
            if not media:
                msg = "❌ 请至少提供一张有效的参考图像 (files, 1-9张)"
                logger.error(msg)
                yield self.create_text_message(msg)
                return
            
            input_params: dict[str, Any] = {
                "media": media
            }
            
            prompt = str(tool_parameters.get("prompt") or "").strip()
            if prompt:
                input_params["prompt"] = prompt[:2500]

            payload: dict[str, Any] = {
                "model": model,
                "input": input_params,
                "parameters": {},
            }

            params = payload["parameters"]

            resolution = tool_parameters.get("resolution")
            if resolution:
                params["resolution"] = str(resolution).strip()

            ratio = tool_parameters.get("ratio")
            if ratio:
                params["ratio"] = str(ratio).strip()

            duration = tool_parameters.get("duration")
            if duration is not None:
                try:
                    params["duration"] = max(3, min(15, int(duration)))
                except (TypeError, ValueError):
                    msg = f"❌ 无效的 duration 参数: {duration}，必须是整数"
                    logger.error(msg)
                    yield self.create_text_message(msg)
                    return

            watermark = tool_parameters.get("watermark")
            if watermark is not None:
                if isinstance(watermark, str):
                    watermark_lower = watermark.lower()
                    if watermark_lower in ["true", "1", "yes"]:
                        params["watermark"] = True
                    elif watermark_lower in ["false", "0", "no"]:
                        params["watermark"] = False
                    else:
                        msg = f"❌ 无效的 watermark 参数: {watermark}，必须是布尔值"
                        logger.error(msg)
                        yield self.create_text_message(msg)
                        return
                else:
                    try:
                        params["watermark"] = bool(watermark)
                    except (TypeError, ValueError):
                        msg = f"❌ 无效的 watermark 参数: {watermark}，必须是布尔值"
                        logger.error(msg)
                        yield self.create_text_message(msg)
                        return

            seed = tool_parameters.get("seed")
            if seed is not None:
                try:
                    params["seed"] = int(seed)
                except (TypeError, ValueError):
                    msg = f"❌ 无效的 seed 参数: {seed}，必须是整数"
                    logger.error(msg)
                    yield self.create_text_message(msg)
                    return

            # Consolidate init message
            init_msg = (
                "🚀 HappyHorse参考图生视频任务启动中...\n"
                f"🤖 使用模型: {model}\n"
                f"🖼️ 参考图像数量: {len(media)}\n"
            )
            if prompt:
                init_msg += f"📝 提示词: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
            init_msg += "⏳ 正在连接通义API..."
            yield self.create_text_message(init_msg)

            debug_payload = json.loads(json.dumps(payload))
            for media_item in debug_payload.get("input", {}).get("media", []):
                media_url = media_item.get("url", "")
                if isinstance(media_url, str) and len(media_url) > 200:
                    media_item["url"] = "data:image/...[Base64 Hidden]"
            logger.info("Request Payload: %s", json.dumps(debug_payload, ensure_ascii=False))

            try:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=15,
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
                result_data = response.json()
            except json.JSONDecodeError as e:
                yield self.create_text_message(f"❌ JSON解析失败: {str(e)}")
                yield self.create_text_message(f"🔧 原始响应: {response.text[:500]}")
                return

            if "code" in result_data:
                error_code = result_data.get("code", "Unknown")
                error_message = result_data.get("message", "Unknown error")
                request_id = result_data.get("request_id", "unknown")
                yield self.create_text_message(
                    f"❌ API错误 ({error_code}): {error_message}"
                )
                yield self.create_text_message(f"Request ID: {request_id}")
                yield self.create_json_message(result_data)
                return

            yield self.create_text_message(
                self._format_response_text(
                    result_data,
                    model=model,
                    prompt=prompt,
                    parameters=params,
                )
            )
            yield self.create_json_message(result_data)
            logger.info("HappyHorse reference-image-to-video task submitted")

        except Exception as e:
            error_msg = f"❌ 生成视频时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _format_response_text(
        result_data: dict[str, Any],
        model: str = "unknown",
        prompt: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> str:
        request_id = result_data.get("request_id", "unknown")
        task_id = result_data.get("output", {}).get("task_id", "unknown")
        task_status = result_data.get("output", {}).get("task_status", "PENDING")
        params = parameters or {}
        resolution = params.get("resolution", "default")
        duration = params.get("duration", "default")
        ratio = params.get("ratio", "default")

        response_text = f"""
🎬 HappyHorse参考图生视频任务已提交！

📋 任务详情:
   • Request ID: {request_id}
   • Task ID: {task_id}
   • Status: {task_status}
   • Model: {model}
   • Resolution: {resolution}
   • Ratio: {ratio}
   • Duration: {duration}s
"""
        if prompt:
            response_text += f"\n📝 Prompt: {prompt}\n"
            
        response_text += f"""
💡 Next Steps:
   • Use the Video Query tool to check progress
   • Task ID: {task_id}
   • Status will update from 'PENDING' → 'RUNNING' → 'SUCCEEDED'/'FAILED'

📊 API Response Summary:
   • Endpoint: /api/v1/services/aigc/video-generation/video-synthesis
   • Method: POST
   • Status: Success (200)
   • Task Status: {task_status}
"""
        return response_text.strip()

    @staticmethod
    def _process_image(image_data: Any) -> str:
        if not image_data:
            return ""

        if isinstance(image_data, str) and (
            image_data.startswith("http") or image_data.startswith("data:")
        ):
            return image_data.strip()

        image_bytes = None
        if hasattr(image_data, "blob"):
            image_bytes = image_data.blob
        elif hasattr(image_data, "read"):
            image_bytes = image_data.read()
        elif isinstance(image_data, bytes):
            image_bytes = image_data

        if not image_bytes:
            return ""

        if len(image_bytes) > 10 * 1024 * 1024:
            raise ValueError("Image size exceeds 10MB")

        try:
            img = Image.open(BytesIO(image_bytes))

            output_fmt = img.format
            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[3])
                img = bg
                output_fmt = "JPEG"
            elif img.mode != "RGB":
                img = img.convert("RGB")
                if not output_fmt:
                    output_fmt = "JPEG"

            buffer = BytesIO()
            save_fmt = output_fmt if output_fmt in ["JPEG", "PNG", "WEBP"] else "JPEG"
            img.save(buffer, format=save_fmt, quality=95)

            b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            mime = "image/jpeg" if save_fmt == "JPEG" else f"image/{save_fmt.lower()}"
            return f"data:{mime};base64,{b64_str}"
        except Exception as e:
            logger.error("Image processing failed: %s", str(e))
            raise ValueError(f"Failed to process image: {str(e)}")