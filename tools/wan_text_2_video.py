from provider.endpoints import api_url as build_api_url
# author: sawyer-shi

import base64
import json
import logging
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)


class WanText2VideoTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Tongyi Wanxiang text-to-video tool (async submit).
        """
        logger.info("Starting wan text-to-video task")

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

            model = tool_parameters.get("model", "wan2.7-t2v").strip()
            prompt = tool_parameters.get("prompt", "").strip()
            if not prompt:
                msg = "❌ 请输入提示词"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            is_wan27 = model.startswith("wan2.7-")

            payload: dict[str, Any] = {
                "model": model,
                "input": {"prompt": prompt},
                "parameters": {},
            }

            input_params = payload["input"]
            if is_wan27:
                prompt_limit = 5000
            elif model.startswith("wan2.6-t2v") or model.startswith("wan2.5-t2v"):
                prompt_limit = 1500
            else:
                prompt_limit = 800
            input_params["prompt"] = prompt[:prompt_limit]

            negative_prompt = tool_parameters.get("negative_prompt", "")
            if negative_prompt:
                input_params["negative_prompt"] = negative_prompt.strip()[:500]

            audio_url = tool_parameters.get("audio_url", "")
            if audio_url and (
                is_wan27
                or model.startswith("wan2.6-t2v")
                or model.startswith("wan2.5-t2v")
            ):
                processed_audio = self._process_audio(audio_url)
                if processed_audio:
                    input_params["audio_url"] = processed_audio

            params = payload["parameters"]

            size = tool_parameters.get("size", "")
            resolution = tool_parameters.get("resolution", "")
            ratio = tool_parameters.get("ratio", "")
            if is_wan27:
                if resolution:
                    params["resolution"] = str(resolution).strip().upper()
                if ratio:
                    params["ratio"] = str(ratio).strip()

                if size and ("resolution" not in params or "ratio" not in params):
                    mapped_resolution, mapped_ratio = self._map_size_to_wan27(size)
                    if mapped_resolution and "resolution" not in params:
                        params["resolution"] = mapped_resolution
                    if mapped_ratio and "ratio" not in params:
                        params["ratio"] = mapped_ratio
            elif size:
                params["size"] = str(size).strip()

            duration = tool_parameters.get("duration")
            if duration is not None:
                try:
                    params["duration"] = int(duration)
                except (TypeError, ValueError):
                    pass

            prompt_extend = tool_parameters.get("prompt_extend")
            if prompt_extend is not None:
                params["prompt_extend"] = prompt_extend

            shot_type = tool_parameters.get("shot_type", "")
            if shot_type and model.startswith("wan2.6-t2v"):
                params["shot_type"] = shot_type.strip()

            audio = tool_parameters.get("audio")
            if audio is not None and (
                model.startswith("wan2.6-t2v") or model.startswith("wan2.5-t2v")
            ):
                params["audio"] = audio

            watermark = tool_parameters.get("watermark")
            if watermark is not None:
                params["watermark"] = watermark

            seed = tool_parameters.get("seed")
            if seed is not None:
                try:
                    params["seed"] = int(seed)
                except (TypeError, ValueError):
                    pass

            yield self.create_text_message("🚀 文生视频任务启动中...")
            yield self.create_text_message(f"🤖 使用模型: {model}")
            yield self.create_text_message(
                f"📝 提示词: {prompt[:100]}{'...' if len(prompt) > 100 else ''}"
            )
            yield self.create_text_message("⏳ 正在连接通义API...")

            debug_payload = json.loads(json.dumps(payload))
            if "audio_url" in debug_payload.get("input", {}) and len(
                debug_payload["input"]["audio_url"]
            ) > 200:
                debug_payload["input"]["audio_url"] = "data:audio/...[Base64 Hidden]"
            logger.info("Request Payload: %s", json.dumps(debug_payload, ensure_ascii=False))

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
                    prompt=input_params.get("prompt", ""),
                    parameters=params,
                )
            )
            yield self.create_json_message(result_data)
            logger.info("Wan text-to-video task submitted")

        except Exception as e:
            error_msg = f"❌ 生成视频时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _map_size_to_wan27(size: Any) -> tuple[str, str]:
        normalized_size = str(size).strip().lower().replace(" ", "")
        mapping = {
            "1280*720": ("720P", "16:9"),
            "720*1280": ("720P", "9:16"),
            "960*960": ("720P", "1:1"),
            "1104*832": ("720P", "4:3"),
            "832*1104": ("720P", "3:4"),
            "1920*1080": ("1080P", "16:9"),
            "1080*1920": ("1080P", "9:16"),
            "1440*1440": ("1080P", "1:1"),
            "1648*1248": ("1080P", "4:3"),
            "1248*1648": ("1080P", "3:4"),
            # Legacy mappings from wan2.6 preset values.
            "1088*832": ("720P", "4:3"),
            "832*1088": ("720P", "3:4"),
            "1632*1248": ("1080P", "4:3"),
            "1248*1632": ("1080P", "3:4"),
        }
        return mapping.get(normalized_size, ("", ""))

    @staticmethod
    def _process_audio(audio_data: Any) -> str:
        if not audio_data:
            return ""

        if hasattr(audio_data, "blob"):
            audio_bytes = audio_data.blob
        elif hasattr(audio_data, "read") and callable(getattr(audio_data, "read")):
            audio_bytes = audio_data.read()
            if isinstance(audio_bytes, str):
                audio_bytes = audio_bytes.encode("utf-8")
        elif isinstance(audio_data, bytes):
            audio_bytes = audio_data
        elif isinstance(audio_data, str) and audio_data.startswith("data:"):
            try:
                _, base64_data = audio_data.split(",", 1)
                audio_bytes = base64.b64decode(base64_data)
            except Exception:
                return ""
        elif isinstance(audio_data, str) and audio_data.startswith(("http://", "https://")):
            return audio_data.strip()
        elif isinstance(audio_data, str) and len(audio_data) < 1000:
            try:
                with open(audio_data, "rb") as audio_file:
                    audio_bytes = audio_file.read()
            except Exception:
                return ""
        elif isinstance(audio_data, str):
            try:
                audio_bytes = base64.b64decode(audio_data)
            except Exception:
                return ""
        else:
            return ""

        if not isinstance(audio_bytes, bytes) or len(audio_bytes) == 0:
            return ""
        if len(audio_bytes) > 15 * 1024 * 1024:
            logger.error("Audio size exceeds 15MB limit")
            return ""

        try:
            if audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xff\xfb"):
                audio_format = "mp3"
            elif audio_bytes.startswith(b"RIFF"):
                audio_format = "wav"
            else:
                audio_format = "mp3"
            base64_string = base64.b64encode(audio_bytes).decode("utf-8")
            return f"data:audio/{audio_format};base64,{base64_string}"
        except Exception as e:
            logger.error("Error processing audio: %s", str(e))
            return ""

    @staticmethod
    def _format_response_text(
        result_data: dict[str, Any],
        model: str = "unknown",
        prompt: str = "unknown",
        parameters: dict[str, Any] | None = None,
    ) -> str:
        request_id = result_data.get("request_id", "unknown")
        task_id = result_data.get("output", {}).get("task_id", "unknown")
        task_status = result_data.get("output", {}).get("task_status", "PENDING")
        params = parameters or {}
        size = params.get("size", "default")
        resolution = params.get("resolution", "")
        ratio = params.get("ratio", "")
        if resolution or ratio:
            size = f"{resolution or 'default'} / {ratio or 'default'}"
        duration = params.get("duration", "default")
        prompt_extend = params.get("prompt_extend", "default")

        response_text = f"""
🎬 文生视频任务已提交！

📋 任务详情:
   • Request ID: {request_id}
   • Task ID: {task_id}
   • Status: {task_status}
   • Model: {model}
   • Resolution: {size}
   • Duration: {duration}s
   • Prompt Extend: {prompt_extend}

📝 Prompt: {prompt}

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
