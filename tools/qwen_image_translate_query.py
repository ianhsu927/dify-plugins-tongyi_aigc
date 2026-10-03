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


class QwenImageTranslateQueryTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Query Tongyi Qwen image translation task.
        """
        logger.info("Starting qwen image translation query")

        try:
            task_id = tool_parameters.get("task_id", "").strip()
            if not task_id:
                yield self.create_text_message("❌ 请输入任务ID")
                return

            api_key = self.runtime.credentials.get("api_key")
            if not api_key:
                yield self.create_text_message("❌ API密钥未配置")
                return

            api_url = build_api_url(self.runtime.credentials, f"/api/v1/tasks/{task_id}")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            yield self.create_text_message("🔍 正在查询图片翻译结果...")
            yield self.create_text_message(f"📋 任务ID: {task_id}")

            try:
                response = requests.get(api_url, headers=headers, timeout=60)
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
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON: %s - %s", str(e), response.text[:300])
                yield self.create_text_message("❌ API 响应解析失败（非JSON）")
                return

            yield self.create_text_message(self._format_response_text(result_data))
            yield self.create_json_message(result_data)

            output = result_data.get("output", {})
            if output.get("task_status") == "SUCCEEDED" and output.get("image_url"):
                image_url = output.get("image_url", "").strip()
                if image_url.startswith("`") and image_url.endswith("`"):
                    image_url = image_url[1:-1].strip()
                if image_url:
                    yield self.create_image_message(image_url)

            logger.info("Image translation query completed")

        except Exception as e:
            error_msg = f"❌ 查询图片翻译结果时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _format_response_text(result_data: dict[str, Any]) -> str:
        request_id = result_data.get("request_id", "unknown")
        output = result_data.get("output", {})
        usage = result_data.get("usage", {})

        task_id = output.get("task_id", "unknown")
        task_status = output.get("task_status", "unknown")
        submit_time = output.get("submit_time", "unknown")
        scheduled_time = output.get("scheduled_time", "unknown")
        end_time = output.get("end_time", "unknown")
        image_url = output.get("image_url", "")
        error_code = output.get("code", "")
        error_message = output.get("message", "")
        image_count = usage.get("image_count", 0)

        if task_status == "SUCCEEDED":
            response_text = f"""
🎉 图片翻译任务完成！

📋 任务详情:
   • 任务ID: {task_id}
   • 状态: {task_status}
   • 提交时间: {submit_time}
   • 调度时间: {scheduled_time}
   • 完成时间: {end_time}
   • 图片数量: {image_count}

📷 结果:
   • 译文图片链接: {image_url}

📊 API 响应摘要:
   • Request ID: {request_id}
   • Endpoint: /api/v1/tasks/{task_id}
   • Method: GET
   • Status: Success (200)
"""
        elif task_status == "FAILED":
            response_text = f"""
❌ 图片翻译任务失败

📋 任务详情:
   • 任务ID: {task_id}
   • 状态: {task_status}
   • 提交时间: {submit_time}
   • 调度时间: {scheduled_time}
   • 完成时间: {end_time}

🚫 错误信息:
   • 错误代码: {error_code}
   • 错误信息: {error_message}

📊 API 响应摘要:
   • Request ID: {request_id}
   • Endpoint: /api/v1/tasks/{task_id}
   • Method: GET
   • Status: Success (200)
"""
        elif task_status == "RUNNING":
            response_text = f"""
⏳ 图片翻译任务处理中

📋 任务详情:
   • 任务ID: {task_id}
   • 状态: {task_status}
   • 提交时间: {submit_time}
   • 调度时间: {scheduled_time}

📊 API 响应摘要:
   • Request ID: {request_id}
   • Endpoint: /api/v1/tasks/{task_id}
   • Method: GET
   • Status: Success (200)
"""
        else:
            response_text = f"""
❓ 图片翻译任务状态未知

📋 任务详情:
   • 任务ID: {task_id}
   • 状态: {task_status}
   • 提交时间: {submit_time}

📊 API 响应摘要:
   • Request ID: {request_id}
   • Endpoint: /api/v1/tasks/{task_id}
   • Method: GET
   • Status: Success (200)
"""

        return response_text.strip()
