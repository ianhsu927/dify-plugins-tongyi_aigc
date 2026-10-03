"""Wan 3.0 unified generation and Wan 2.7 video editing."""
import json
from collections import Counter
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from provider.endpoints import api_url

MODELS = {"wan3.0-video", "wan3.0-video-prime", "wan2.7-videoedit"}
LIMITS = {"first_frame": 1, "last_frame": 1, "reference_image": 10,
          "reference_video": 5, "reference_audio": 5, "file": 1, "link": 1}


def integer(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} 必须为整数")
    result = int(value)
    if str(value).strip() != str(result) and value != result:
        raise ValueError(f"{name} 必须为整数")
    return result


def build_payload(parameters):
    model = parameters.get("model") or "wan3.0-video"
    if model not in MODELS:
        raise ValueError("不支持的模型")
    is_edit = model == "wan2.7-videoedit"
    prompt = str(parameters.get("prompt") or "").strip()
    raw = parameters.get("media") or "[]"
    media = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(media, list):
        raise ValueError("media 必须为 JSON 数组")
    allowed = {"video": 1, "reference_image": 4} if is_edit else LIMITS
    clean = []
    for item in media:
        if not isinstance(item, dict) or item.get("type") not in allowed:
            raise ValueError("media 包含不支持的素材类型")
        url = item.get("url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://", "oss://", "data:image/")):
            raise ValueError("素材必须提供公开 URL、临时 OSS URL 或图像 Base64")
        if url.startswith("data:") and item["type"] not in {"first_frame", "last_frame", "reference_image"}:
            raise ValueError("仅图像素材支持 Base64")
        if item["type"] == "link" and not url.startswith(("https://", "http://")):
            raise ValueError("网页素材必须使用 HTTP/HTTPS URL")
        clean.append({"type": item["type"], "url": url})
    counts = Counter(x["type"] for x in clean)
    if any(counts[k] > allowed[k] for k in counts):
        raise ValueError("素材数量超过模型限制")
    if is_edit:
        if not prompt or counts["video"] != 1:
            raise ValueError("视频编辑需要提示词及一个 type=video 素材")
    else:
        if not prompt and not clean:
            raise ValueError("提示词和素材至少提供一项")
        frames = {"first_frame", "last_frame"} & counts.keys()
        if frames and set(counts) - {"first_frame", "last_frame"}:
            raise ValueError("首尾帧不能与参考素材混用")
        if counts["last_frame"] and not counts["first_frame"]:
            raise ValueError("尾帧需要同时提供首帧")
        if counts["file"] and counts["link"]:
            raise ValueError("文档和网页不能同时输入")
    input_data = {}
    if prompt:
        input_data["prompt"] = prompt[:5000 if is_edit else 20000]
    if clean:
        input_data["media"] = clean
    if is_edit and parameters.get("negative_prompt"):
        input_data["negative_prompt"] = str(parameters["negative_prompt"])[:500]
    output = {}
    resolution = parameters.get("resolution") or "1080P"
    if resolution not in ({"720P", "1080P"} if is_edit else {"480P", "720P", "1080P"}):
        raise ValueError("模型不支持该分辨率")
    output["resolution"] = resolution
    if not is_edit:
        ratio = parameters.get("ratio") or "adaptive"
        if ratio not in {"adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"}:
            raise ValueError("不支持的宽高比")
        output["ratio"] = ratio
    if parameters.get("duration") is not None:
        duration = integer(parameters["duration"], "duration")
        if not (2 <= duration <= (10 if is_edit else 30) or (not is_edit and duration == -1)):
            raise ValueError("视频时长超出模型支持范围")
        output["duration"] = duration
    for key in ("prompt_extend", "watermark", "audio"):
        if key == "audio" and is_edit:
            continue
        if parameters.get(key) is not None:
            value = parameters[key]
            if not isinstance(value, bool):
                raise ValueError(f"{key} 必须为布尔值")
            output[key] = value
    if (counts["file"] or counts["link"]) and output.get("prompt_extend") is False:
        raise ValueError("文档/网页生视频必须开启提示词改写")
    if is_edit and parameters.get("audio_setting"):
        if parameters["audio_setting"] not in {"auto", "origin"}:
            raise ValueError("audio_setting 必须为 auto 或 origin")
        output["audio_setting"] = parameters["audio_setting"]
    if parameters.get("seed") is not None:
        seed = integer(parameters["seed"], "seed")
        if not (0 <= seed <= 2147483647 or (not is_edit and seed == -1)):
            raise ValueError("seed 超出模型支持范围")
        output["seed"] = seed
    return {"model": model, "input": input_data, "parameters": output}


class WanVideoTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        try:
            key = self.runtime.credentials.get("api_key")
            if not key:
                raise ValueError("API密钥未配置")
            payload = build_payload(tool_parameters)
            response = requests.post(
                api_url(self.runtime.credentials, "/api/v1/services/aigc/video-generation/video-synthesis"),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                         "X-DashScope-Async": "enable"}, json=payload, timeout=60)
            data = response.json()
            task_id = data.get("output", {}).get("task_id")
            if response.status_code != 200 or not task_id or data.get("code"):
                yield self.create_text_message(f"❌ 视频任务提交失败: {data.get('code', response.status_code)} {data.get('message', '')}")
                return
            yield self.create_json_message(data)
            yield self.create_text_message(f"视频任务已提交：{task_id}。请使用 wan_video_query 查询结果。")
        except (ValueError, TypeError, requests.RequestException) as error:
            yield self.create_text_message(f"❌ {error}")
