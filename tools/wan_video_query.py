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


class WanVideoQueryTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Query Tongyi Wanxiang video generation task status and results.
        """
        logger.info("Starting wan video query")

        try:
            task_id = tool_parameters.get("task_id", "").strip()
            if not task_id:
                yield self.create_text_message("❌ 请输入任务ID")
                return

            api_key = self.runtime.credentials.get("api_key")
            if not api_key:
                yield self.create_text_message("❌ API密钥未配置")
                return

            download_video = tool_parameters.get("download_video", "false") == "true"

            api_url = build_api_url(self.runtime.credentials, f"/api/v1/tasks/{task_id}")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            yield self.create_text_message("🔍 正在查询视频生成结果...")
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
            task_status = output.get("task_status")
            video_url = output.get("video_url")
            last_frame_url = output.get("last_frame_url")

            if task_status == "SUCCEEDED":
                if video_url:
                    yield self.create_text_message(f"🎬 视频链接: {video_url}")
                    if download_video:
                        yield self.create_text_message("⬇️ 正在下载视频文件...")
                        try:
                            video_response = requests.get(video_url, timeout=120)
                            if video_response.status_code == 200:
                                yield self.create_blob_message(
                                    blob=video_response.content,
                                    meta={
                                        "mime_type": "video/mp4",
                                        "filename": f"{task_id}.mp4",
                                    },
                                )
                                yield self.create_text_message("✅ 视频下载完成")
                            else:
                                yield self.create_text_message(
                                    f"❌ 视频下载失败，状态码: {video_response.status_code}"
                                )
                        except requests.exceptions.RequestException as e:
                            yield self.create_text_message(f"❌ 视频下载失败: {str(e)}")
                if last_frame_url:
                    yield self.create_text_message(f"🖼️ 尾帧链接: {last_frame_url}")

            logger.info("Wan video query completed")

        except Exception as e:
            error_msg = f"❌ 查询视频结果时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    @staticmethod
    def _format_response_text(result_data: dict[str, Any]) -> str:
        output = result_data.get("output", {})
        usage = result_data.get("usage", {})

        task_id = output.get("task_id", "unknown")
        task_status = output.get("task_status", "unknown")
        submit_time = output.get("submit_time", "unknown")
        scheduled_time = output.get("scheduled_time", "unknown")
        end_time = output.get("end_time", "unknown")
        video_url = output.get("video_url", "")
        orig_prompt = output.get("orig_prompt", "")
        actual_prompt = output.get("actual_prompt", "")

        duration = usage.get("duration", 0)
        input_video_duration = usage.get("input_video_duration", 0)
        output_video_duration = usage.get("output_video_duration", 0)
        video_count = usage.get("video_count", 0)
        sr = usage.get("SR", 0)
        size = usage.get("size", "")

        if task_status == "SUCCEEDED":
            response_text = f"""
🎬 万相视频任务成功

📋 任务详情:
   • 任务ID: {task_id}
   • 状态: {task_status}
   • 提交时间: {submit_time}
   • 调度时间: {scheduled_time}
   • 完成时间: {end_time}

📹 视频信息:
   • 视频链接: {video_url}
   • 视频时长: {output_video_duration}s
   • 视频数量: {video_count}
   • 分辨率: {sr}P ({size})

📝 原始提示词:
   {orig_prompt}
"""
            if actual_prompt:
                response_text += f"""

📝 优化后提示词:
   {actual_prompt}
"""
            response_text += f"""

📊 使用统计:
   • 总时长: {duration}s
   • 输入视频时长: {input_video_duration}s
   • 输出视频时长: {output_video_duration}s
"""
        elif task_status == "FAILED":
            error_code = output.get("code", "Unknown")
            error_message = output.get("message", "Unknown error")
            response_text = f"""
❌ 万相视频任务失败

📋 任务详情:
   • 任务ID: {task_id}
   • 状态: {task_status}
   • 提交时间: {submit_time}
   • 错误代码: {error_code}
   • 错误信息: {error_message}

📝 原始提示词:
   {orig_prompt}
"""
        else:
            response_text = f"""
⏳ 万相视频任务处理中

📋 任务详情:
   • 任务ID: {task_id}
   • 状态: {task_status}
   • 提交时间: {submit_time}
   • 调度时间: {scheduled_time}

📝 原始提示词:
   {orig_prompt}
"""

        return response_text.strip()
