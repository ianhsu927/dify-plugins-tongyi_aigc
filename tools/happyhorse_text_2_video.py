from provider.endpoints import api_url as build_api_url
import json
import logging
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)

class HappyHorseText2VideoTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        HappyHorse text-to-video tool (async submit).
        """
        logger.info("Starting HappyHorse text-to-video task")

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

            model = tool_parameters.get("model", "happyhorse-1.1-t2v").strip()
            prompt = tool_parameters.get("prompt", "").strip()
            if not prompt:
                msg = "❌ 请输入提示词"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            prompt_limit = 2500
            prompt = prompt[:prompt_limit]

            payload: dict[str, Any] = {
                "model": model,
                "input": {"prompt": prompt},
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
                    params["duration"] = int(duration)
                except (TypeError, ValueError):
                    msg = f"❌ 无效的 duration 参数: {duration}"
                    logger.error(msg)
                    yield self.create_text_message(msg)
                    return
            
            watermark = tool_parameters.get("watermark")
            if watermark is not None:
                params["watermark"] = watermark

            seed = tool_parameters.get("seed")
            if seed is not None:
                try:
                    params["seed"] = int(seed)
                except (TypeError, ValueError):
                    msg = f"❌ 无效的 seed 参数: {seed}"
                    logger.error(msg)
                    yield self.create_text_message(msg)
                    return

            yield self.create_text_message(
                "🚀 HappyHorse文生视频任务启动中...\n"
                f"🤖 使用模型: {model}\n"
                f"📝 提示词: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
                "⏳ 正在连接通义API..."
            )

            logger.info("Request Payload: %s", json.dumps(payload, ensure_ascii=False))

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
            logger.info("HappyHorse text-to-video task submitted")

        except Exception as e:
            error_msg = f"❌ 生成视频时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

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
        resolution = params.get("resolution", "default")
        ratio = params.get("ratio", "default")
        duration = params.get("duration", "default")

        response_text = f"""
🎬 HappyHorse文生视频任务已提交！

📋 任务详情:
   • Request ID: {request_id}
   • Task ID: {task_id}
   • Status: {task_status}
   • Model: {model}
   • Resolution: {resolution}
   • Ratio: {ratio}
   • Duration: {duration}s

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
