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

_ALLOWED_IMAGE_FORMATS = {"JPEG", "JPG", "PNG", "WEBP"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


class HappyHorseVideoEditTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        logger.info("Starting HappyHorse video-edit task")

        try:
            api_key = self.runtime.credentials.get("api_key")
            if not api_key:
                msg = "❌ API密钥未配置"
                logger.error(msg)
                yield self.create_text_message(msg)
                return

            prompt = str(tool_parameters.get("prompt") or "").strip()
            if not prompt:
                msg = "❌ 请输入提示词"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return
            prompt = prompt[:2500]

            video_url = str(tool_parameters.get("video_url") or "").strip()
            if not video_url:
                msg = "❌ 请输入视频链接"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return
            if not (video_url.startswith("http://") or video_url.startswith("https://")):
                msg = "❌ video_url 必须以 http:// 或 https:// 开头"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            model = str(tool_parameters.get("model") or "happyhorse-1.0-video-edit").strip()

            media: list[dict[str, str]] = [{"type": "video", "url": video_url}]
            reference_image_count = 0
            
            files = tool_parameters.get("files")
            if files:
                if isinstance(files, list):
                    file_list = files
                else:
                    file_list = [files]
                for file_obj in file_list:
                    try:
                        processed = self._process_image(file_obj)
                    except ValueError as err:
                        msg = f"❌ 参考图片处理失败: {str(err)}"
                        logger.error(msg)
                        yield self.create_text_message(msg)
                        return
                    media.append({"type": "reference_image", "url": processed})
                    reference_image_count += 1

            payload: dict[str, Any] = {
                "model": model,
                "input": {"prompt": prompt, "media": media},
                "parameters": {},
            }

            params = payload["parameters"]

            resolution = tool_parameters.get("resolution")
            if resolution is not None and str(resolution).strip() != "":
                resolution_value = str(resolution).strip()
                if resolution_value not in {"720P", "1080P"}:
                    msg = "❌ resolution 仅支持 720P 或 1080P"
                    logger.error(msg)
                    yield self.create_text_message(msg)
                    return
                params["resolution"] = resolution_value

            audio_setting = tool_parameters.get("audio_setting")
            if audio_setting is not None and str(audio_setting).strip() != "":
                audio_setting_value = str(audio_setting).strip()
                if audio_setting_value not in {"auto", "origin"}:
                    msg = "❌ audio_setting 仅支持 auto 或 origin"
                    logger.error(msg)
                    yield self.create_text_message(msg)
                    return
                params["audio_setting"] = audio_setting_value

            watermark = tool_parameters.get("watermark")
            if watermark is not None:
                try:
                    params["watermark"] = self._parse_bool(watermark)
                except ValueError as err:
                    msg = f"❌ {str(err)}"
                    logger.error(msg)
                    yield self.create_text_message(msg)
                    return

            seed = tool_parameters.get("seed")
            if seed is not None and str(seed).strip() != "":
                try:
                    seed_value = int(seed)
                except (TypeError, ValueError):
                    msg = "❌ seed 必须是整数"
                    logger.error(msg)
                    yield self.create_text_message(msg)
                    return
                if seed_value < 0 or seed_value > 2147483647:
                    msg = "❌ seed 必须在 0 到 2147483647 之间"
                    logger.error(msg)
                    yield self.create_text_message(msg)
                    return
                params["seed"] = seed_value

            api_url = build_api_url(self.runtime.credentials, "/api/v1/services/aigc/video-generation/video-synthesis")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }

            debug_payload = json.loads(json.dumps(payload))
            for media_item in debug_payload.get("input", {}).get("media", []):
                media_url = media_item.get("url", "")
                if isinstance(media_url, str) and media_url.startswith("data:image/"):
                    media_item["url"] = "data:image/...[Base64 Hidden]"
            logger.info("Request payload: %s", json.dumps(debug_payload, ensure_ascii=False))

            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=15)
            except requests.exceptions.Timeout:
                msg = "❌ 请求超时，请稍后重试"
                logger.error(msg)
                yield self.create_text_message(msg)
                return
            except requests.exceptions.RequestException as err:
                msg = f"❌ 请求失败: {str(err)}"
                logger.error(msg)
                yield self.create_text_message(msg)
                return

            if response.status_code != 200:
                logger.error("API status %s: %s", response.status_code, response.text[:500])
                yield self.create_text_message(f"❌ API 响应状态码: {response.status_code}")
                if response.text:
                    yield self.create_text_message(f"🔧 响应内容: {response.text[:500]}")
                return

            try:
                result_data = response.json()
            except json.JSONDecodeError as err:
                logger.error("JSON parse failed: %s", str(err))
                yield self.create_text_message(f"❌ JSON解析失败: {str(err)}")
                yield self.create_text_message(f"🔧 原始响应: {response.text[:500]}")
                return

            if "code" in result_data:
                error_code = result_data.get("code", "Unknown")
                error_message = result_data.get("message", "Unknown error")
                request_id = result_data.get("request_id", "unknown")
                yield self.create_text_message(f"❌ API错误 ({error_code}): {error_message}")
                yield self.create_text_message(f"Request ID: {request_id}")
                yield self.create_json_message(result_data)
                return

            yield self.create_text_message(
                self._format_response_text(
                    result_data=result_data,
                    model=model,
                    prompt=prompt,
                    parameters=params,
                    video_url=video_url,
                    reference_image_count=reference_image_count,
                )
            )
            yield self.create_json_message(result_data)
            logger.info("HappyHorse video-edit task submitted")
        except Exception as err:
            error_msg = f"❌ 生成视频时出现未预期错误: {str(err)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            raise ValueError("watermark 必须是布尔值")
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y", "on"}:
                return True
            if normalized in {"false", "0", "no", "n", "off"}:
                return False
            raise ValueError("watermark 必须是布尔值")
        raise ValueError("watermark 必须是布尔值")

    @staticmethod
    def _process_image(image_data: Any) -> str:
        if image_data is None:
            raise ValueError("图片不能为空")

        if isinstance(image_data, str):
            data_uri = image_data.strip()
            if not data_uri.startswith("data:image/"):
                raise ValueError("仅支持 data URI 格式字符串")
            if ";base64," not in data_uri:
                raise ValueError("data URI 必须包含 base64 数据")

            header, b64_data = data_uri.split(",", 1)
            mime = header[5:].split(";")[0].lower()
            if mime not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
                raise ValueError("仅支持 JPEG/JPG/PNG/WEBP 图片")

            try:
                raw_bytes = base64.b64decode(b64_data, validate=True)
            except Exception as err:
                raise ValueError("data URI base64 数据无效") from err

            if len(raw_bytes) > _MAX_IMAGE_BYTES:
                raise ValueError("图片大小不能超过10MB")

            return data_uri

        image_bytes: bytes | None = None
        if hasattr(image_data, "blob"):
            image_bytes = image_data.blob
        elif hasattr(image_data, "read"):
            image_bytes = image_data.read()
        elif isinstance(image_data, (bytes, bytearray)):
            image_bytes = bytes(image_data)

        if not image_bytes:
            raise ValueError("无法读取图片内容")

        if len(image_bytes) > _MAX_IMAGE_BYTES:
            raise ValueError("图片大小不能超过10MB")

        try:
            img = Image.open(BytesIO(image_bytes))
            source_format = (img.format or "").upper()
            if source_format not in _ALLOWED_IMAGE_FORMATS:
                raise ValueError("仅支持 JPEG/JPG/PNG/WEBP 图片")

            save_format = "JPEG" if source_format == "JPG" else source_format
            if save_format not in {"JPEG", "PNG", "WEBP"}:
                save_format = "JPEG"

            if save_format == "JPEG":
                if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                ):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")

            buffer = BytesIO()
            save_kwargs: dict[str, Any] = {"format": save_format}
            if save_format == "JPEG":
                save_kwargs["quality"] = 95
            img.save(buffer, **save_kwargs)

            output_bytes = buffer.getvalue()
            if len(output_bytes) > _MAX_IMAGE_BYTES:
                raise ValueError("图片处理后大小不能超过10MB")

            mime = "image/jpeg" if save_format == "JPEG" else f"image/{save_format.lower()}"
            encoded = base64.b64encode(output_bytes).decode("utf-8")
            return f"data:{mime};base64,{encoded}"
        except ValueError:
            raise
        except Exception as err:
            logger.error("Image processing failed: %s", str(err))
            raise ValueError("图片处理失败") from err

    @staticmethod
    def _format_response_text(
        result_data: dict[str, Any],
        model: str,
        prompt: str,
        parameters: dict[str, Any],
        video_url: str,
        reference_image_count: int,
    ) -> str:
        request_id = result_data.get("request_id", "unknown")
        output = result_data.get("output", {})
        task_id = output.get("task_id", "unknown")
        task_status = output.get("task_status", "PENDING")

        prompt_preview = prompt[:100]
        if len(prompt) > 100:
            prompt_preview += "..."

        details = [
            "🎬 HappyHorse视频编辑任务已提交！",
            "",
            "📋 任务详情:",
            f"   • Request ID: {request_id}",
            f"   • Task ID: {task_id}",
            f"   • Status: {task_status}",
            f"   • Model: {model}",
            f"   • Video URL: {video_url}",
            f"   • Reference Images: {reference_image_count}",
        ]

        if "resolution" in parameters:
            details.append(f"   • Resolution: {parameters['resolution']}")
        if "audio_setting" in parameters:
            details.append(f"   • Audio Setting: {parameters['audio_setting']}")
        if "watermark" in parameters:
            details.append(f"   • Watermark: {parameters['watermark']}")
        if "seed" in parameters:
            details.append(f"   • Seed: {parameters['seed']}")

        details.extend(
            [
                f"📝 Prompt Preview: {prompt_preview}",
                "",
                "💡 Next Steps:",
                "   • Use the Video Query tool to check progress",
                f"   • Task ID: {task_id}",
                "   • Status will update from 'PENDING' -> 'RUNNING' -> 'SUCCEEDED'/'FAILED'",
            ]
        )

        return "\n".join(details)
