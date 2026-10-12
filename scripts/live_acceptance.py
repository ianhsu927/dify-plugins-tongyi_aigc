"""Opt-in real service smoke test. Generation and credential probe may cost money."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dify_plugin.entities.tool import ToolRuntime
from provider.tongyi_aigc import TongyiAigcProvider
from tools.qwen_text_2_image import QwenText2ImageTool
from tools.wan_video import WanVideoTool
from tools.wan_video_query import WanVideoQueryTool

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['credentials', 'image', 'video', 'edit', 'query'])
parser.add_argument('--allow-paid', action='store_true')
parser.add_argument('--task-id')
parser.add_argument('--video-url')
args = parser.parse_args()
if args.action != 'query' and not args.allow_paid:
    parser.error('This action may incur charges; explicitly pass --allow-paid')
credentials = {'api_key': os.environ.get('DASHSCOPE_API_KEY'),
               'api_base_url': os.environ.get('DASHSCOPE_API_BASE_URL')}
if not credentials['api_key']:
    parser.error('Set DASHSCOPE_API_KEY in the environment; do not put it in command arguments')
if args.action == 'credentials':
    TongyiAigcProvider()._validate_credentials(credentials)
    print('qwen-plus credential probe passed; image/video permissions are NOT proven')
    sys.exit(0)
params = {'prompt': 'A red ball on a white background', 'duration':2, 'resolution':'480P'}
cls = WanVideoTool
if args.action == 'image':
    cls = QwenText2ImageTool
    params = {'model':'qwen-image-3.0-pro', 'prompt': 'A red ball on a white background', 'n':1, 'enable_thinking':False}
elif args.action == 'edit':
    if not args.video_url:
        parser.error('Provide --video-url with a publicly accessible authorized test clip')
    params = {'model':'wan2.7-videoedit','prompt':'Change the ball to blue', 'resolution':'720P',
              'media':json.dumps([{'type':'video','url':args.video_url}]), 'audio_setting':'origin'}
elif args.action == 'query':
    if not args.task_id:
        parser.error('Provide --task-id from the actual submit response')
    cls = WanVideoQueryTool
    params = {'task_id':args.task_id, 'download_video':'false'}
runtime = ToolRuntime(credentials=credentials, user_id=None, session_id=None)
messages = list(cls(runtime, None)._invoke(params))
for message in messages:
    print(message.model_dump_json())
if any('❌' in str(message) for message in messages):
    sys.exit(1)
if args.action in {'video','edit'}:
    if not any(message.type.value == 'json' and message.message.json_object.get('output',{}).get('task_id') for message in messages):
        sys.exit(1)
if args.action == 'image' and not any(message.type.value == 'image' for message in messages):
    sys.exit(1)
# Query exit 0 means HTTP/serialization worked; inspect task_status for completion.
