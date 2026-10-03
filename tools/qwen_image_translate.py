from provider.endpoints import api_url as build_api_url
# author: sawyer-shi

import json
import logging
import time
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)


class QwenImageTranslateTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Tongyi Qwen image translation tool.
        """
        logger.info("Starting qwen image translation task")

        try:
            api_key = self.runtime.credentials.get("api_key")
            if not api_key:
                msg = "❌ API密钥未配置"
                logger.error(msg)
                yield self.create_text_message(msg)
                return

            image_url = tool_parameters.get("image_url", "").strip()
            if not image_url:
                msg = "❌ 请提供图片URL"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            target_lang = tool_parameters.get("target_lang", "").strip()
            if not target_lang:
                msg = "❌ 请提供目标语言"
                logger.warning(msg)
                yield self.create_text_message(msg)
                return

            model = tool_parameters.get("model", "qwen-mt-image")
            source_lang = tool_parameters.get("source_lang", "auto")

            payload: dict[str, Any] = {
                "model": model,
                "input": {
                    "image_url": image_url,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                },
            }

            domain_hint = tool_parameters.get("domain_hint", "")
            if domain_hint:
                payload["input"].setdefault("ext", {})
                payload["input"]["ext"]["domainHint"] = domain_hint

            sensitives = tool_parameters.get("sensitives", "")
            if sensitives:
                try:
                    sensitives_array = json.loads(sensitives)
                except json.JSONDecodeError:
                    yield self.create_text_message("❌ 敏感词参数必须是JSON数组")
                    return
                payload["input"].setdefault("ext", {})
                payload["input"]["ext"]["sensitives"] = sensitives_array

            terminologies = tool_parameters.get("terminologies", "")
            if terminologies:
                try:
                    terminologies_array = json.loads(terminologies)
                except json.JSONDecodeError:
                    yield self.create_text_message("❌ 术语参数必须是JSON数组")
                    return
                payload["input"].setdefault("ext", {})
                payload["input"]["ext"]["terminologies"] = terminologies_array

            skip_img_segment = tool_parameters.get("skip_img_segment")
            if skip_img_segment is not None:
                payload["input"].setdefault("ext", {})
                payload["input"]["ext"].setdefault("config", {})
                payload["input"]["ext"]["config"]["skipImgSegment"] = bool(
                    skip_img_segment
                )

            api_url = build_api_url(self.runtime.credentials, "/api/v1/services/aigc/image2image/image-synthesis")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }

            yield self.create_text_message("🚀 图片翻译任务启动中...")
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
                logger.error("API status %s: %s", response.status_code, response.text[:300])
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

            yield self.create_text_message("✅ 翻译任务已提交")
            yield self.create_json_message(result_data)

            output = result_data.get("output", {})
            task_id = output.get("task_id")
            if not task_id:
                yield self.create_text_message("❌ 未获取到任务ID")
                return
            yield self.create_text_message(f"📋 任务ID: {task_id}")

            task_result = self._check_task_status(task_id, api_key)
            if not task_result:
                yield self.create_text_message("❌ 查询任务结果失败")
                return

            yield self.create_text_message(self._format_task_result(task_result))
            yield self.create_json_message(task_result)

            output = task_result.get("output", {})
            if output.get("task_status") == "SUCCEEDED":
                results = output.get("results", [])
                for result in results:
                    if "url" in result:
                        yield self.create_image_message(result["url"])

            logger.info("Image translation task completed")

        except Exception as e:
            error_msg = f"❌ 翻译图像时出现未预期错误: {str(e)}"
            logger.exception(error_msg)
            yield self.create_text_message(error_msg)

    def _check_task_status(self, task_id: str, api_key: str) -> dict[str, Any] | None:
        max_attempts = 30
        attempt = 0
        api_url = build_api_url(self.runtime.credentials, f"/api/v1/tasks/{task_id}")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        while attempt < max_attempts:
            try:
                response = requests.get(api_url, headers=headers, timeout=60)
            except requests.exceptions.RequestException:
                return None

            if response.status_code == 200:
                try:
                    result_data = response.json()
                except json.JSONDecodeError:
                    return None

                output = result_data.get("output", {})
                status = output.get("task_status")
                if status == "SUCCEEDED":
                    return result_data
                if status == "FAILED":
                    return {"error": result_data.get("message", "Task failed"), "output": output}
                if status in {"PENDING", "RUNNING"}:
                    attempt += 1
                    time.sleep(5)
                    continue
                return result_data
            return None

        return {"error": "Task did not complete within the expected time", "status": "TIMEOUT"}

    @staticmethod
    def _format_task_result(task_result: dict[str, Any]) -> str:
        output = task_result.get("output", {})
        task_status = output.get("task_status", "unknown")
        if task_status == "SUCCEEDED":
            results = output.get("results", [])
            result_count = len(results)
            result_info = ""
            if result_count > 0:
                first_result = results[0]
                if "url" in first_result:
                    result_info = f"   • 结果链接: {first_result['url']}\n"
                if "width" in first_result and "height" in first_result:
                    result_info += (
                        f"   • 尺寸: {first_result['width']}x{first_result['height']}\n"
                    )
            response_text = f"""
✅ 图片翻译成功！

📋 任务结果:
   • 状态: {task_status}
   • 结果数量: {result_count}
{result_info}
"""
        else:
            error_msg = task_result.get("error", "Unknown error")
            response_text = f"""
❌ 图片翻译失败！

📋 任务结果:
   • 状态: {task_status}
   • 错误: {error_msg}
"""
        return response_text.strip()
