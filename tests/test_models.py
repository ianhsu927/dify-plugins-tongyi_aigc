import importlib
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml
from dify_plugin.entities.tool import ToolRuntime
from dify_plugin.entities.tool import ToolConfiguration, ToolProviderConfiguration
from provider.endpoints import api_url
from tools.wan_video import WanVideoTool, build_payload
from tools.qwen_text_2_image import QwenText2ImageTool
from tools.qwen_image_2_image import QwenImage2ImageTool
from tools.wan_video_query import WanVideoQueryTool
from tools.wan_text_2_image import WanText2ImageTool

HOST = 'https://test.cn-beijing.maas.aliyuncs.com'


def tool(cls):
    return cls(ToolRuntime(credentials={'api_key': 'test-key', 'api_base_url': HOST},
                           user_id=None, session_id=None), None)


def response(data, status=200):
    return Mock(status_code=status, json=Mock(return_value=data), text=json.dumps(data))


class ModelsTest(unittest.TestCase):
    def test_schema_and_imports(self):
        manifest = yaml.safe_load(Path('manifest.yaml').read_text())
        self.assertEqual(manifest['version'], manifest['meta']['version'])
        provider = yaml.safe_load(Path('provider/tongyi_aigc.yaml').read_text())
        ToolProviderConfiguration.model_validate(provider)
        for path in yaml.safe_load(Path('provider/tongyi_aigc.yaml').read_text())['tools']:
            schema = yaml.safe_load(Path(path).read_text())
            ToolConfiguration.model_validate(schema)
            mod = importlib.import_module(schema['extra']['python']['source'][:-3].replace('/', '.'))
            self.assertIsNotNone(mod)
            for field in schema['parameters']:
                if field.get('options') and field.get('default') is not None:
                    self.assertIn(field['default'], [x['value'] for x in field['options']])

    def test_endpoints(self):
        self.assertEqual(api_url({}, '/api/v1/tasks/id'), 'https://dashscope.aliyuncs.com/api/v1/tasks/id')
        self.assertEqual(api_url({'api_base_url': HOST + '/'}, '/api/v1/tasks/id'), HOST + '/api/v1/tasks/id')
        for host in ['http://dashscope.aliyuncs.com', 'https://example.com', HOST+'/api', HOST+'?x=1']:
            with self.assertRaises(ValueError):
                api_url({'api_base_url': host}, '/api')

    def test_wan3_all_modes(self):
        for model in ['wan3.0-video', 'wan3.0-video-prime']:
            payload = build_payload({'model': model, 'prompt': '生成视频', 'duration': 30, 'resolution': '480P', 'seed': -1})
            self.assertEqual(payload['parameters']['duration'], 30)
        for types in [['first_frame'], ['first_frame','last_frame'], ['reference_image','reference_audio'], ['reference_video'], ['file'], ['link']]:
            payload = build_payload({'media': json.dumps([{'type': t, 'url': 'https://example.com/a'} for t in types]), 'duration': -1})
            self.assertEqual([m['type'] for m in payload['input']['media']], types)

    def test_invalid_wan_media(self):
        for params in [{}, {'media': '{}'}, {'duration': 31,'prompt':'p'}, {'duration': 2.5,'prompt':'p'}, {'media': '[{"type":"last_frame","url":"https://x/a"}]'},
                       {'media': json.dumps([{'type': t,'url':'https://x/a'} for t in ['first_frame','reference_image']])},
                       {'media': json.dumps([{'type': t,'url':'https://x/a'} for t in ['file','link']])},
                       {'media':'[{"type":"file","url":"https://x/a"}]','prompt_extend':False},
                       {'media':json.dumps([{'type':'reference_image','url':'https://x/a'}]*11)},
                       {'model':'wan2.7-videoedit','prompt':'p','media':'[]'}]:
            with self.subTest(params=params), self.assertRaises((ValueError, TypeError)):
                build_payload(params)

    def test_wan_edit(self):
        p = build_payload({'model':'wan2.7-videoedit','prompt':'编辑','media':'[{"type":"video","url":"https://x/a.mp4"}]','duration':10,'audio_setting':'origin'})
        self.assertNotIn('ratio', p['parameters'])
        self.assertNotIn('audio', p['parameters'])

    def test_wan_submit_and_query_same_host(self):
        with patch('tools.wan_video.requests.post', return_value=response({'output':{'task_id':'task123','task_status':'PENDING'}})) as post:
            messages = list(tool(WanVideoTool)._invoke({'prompt':'p'}))
            self.assertTrue(messages)
            self.assertEqual(post.call_args.args[0], HOST+'/api/v1/services/aigc/video-generation/video-synthesis')
            self.assertEqual(post.call_args.kwargs['headers']['X-DashScope-Async'], 'enable')
        with patch('tools.wan_video_query.requests.get', return_value=response({'output':{'task_id':'task123','task_status':'SUCCEEDED','video_url':'https://x/video.mp4'}})) as get:
            list(tool(WanVideoQueryTool)._invoke({'task_id':'task123'}))
            self.assertEqual(get.call_args.args[0], HOST+'/api/v1/tasks/task123')

    def test_submit_error(self):
        with patch('tools.wan_video.requests.post', return_value=response({'code':'InvalidParameter','message':'bad'},400)):
            messages = list(tool(WanVideoTool)._invoke({'prompt':'p'}))
            self.assertIn('InvalidParameter', str(messages))

    def test_qwen3_request_and_image_response(self):
        data={'output':{'choices':[{'message':{'content':[{'image':'https://x/image.png'}]}}]}}
        for model in ['qwen-image-3.0-pro','qwen-image-3.0','qwen-image-2.0-pro-2026-06-22','qwen-image-2.0-pro-2026-04-22']:
            with self.subTest(model=model), patch('tools.qwen_text_2_image.requests.post', return_value=response(data)) as post:
                messages=list(tool(QwenText2ImageTool)._invoke({'model':model,'prompt':'文'*1000,'n':6,'enable_thinking':True,'prompt_extend_mode':'agent'}))
                payload=post.call_args.kwargs['json']
                self.assertEqual(len(payload['input']['messages'][0]['content'][0]['text']),1000)
                self.assertEqual(payload['parameters']['n'],6)
                self.assertIn('image.png', str(messages))
                if model.startswith('qwen-image-3.0'):
                    self.assertNotIn('size',payload['parameters'])
                    self.assertEqual(payload['parameters']['prompt_extend_mode'],'agent')
                else:
                    self.assertNotIn('enable_thinking',payload['parameters'])

    def test_qwen3_edit(self):
        data={'output':{'choices':[{'message':{'content':[{'image':'https://x/image.png'}]}}]}}
        with patch.object(QwenImage2ImageTool,'_process_image',return_value='data:image/png;base64,AA'), patch('tools.qwen_image_2_image.requests.post',return_value=response(data)) as post:
            list(tool(QwenImage2ImageTool)._invoke({'prompt':'编辑','images':[b'fake'],'enable_thinking':True,'n':6}))
            payload=post.call_args.kwargs['json']
            self.assertEqual(payload['model'],'qwen-image-3.0-pro')
            self.assertTrue(payload['parameters']['enable_thinking'])
        with patch.object(QwenImage2ImageTool,'_process_image',return_value='data:image/png;base64,AA'), patch('tools.qwen_image_2_image.requests.post') as post:
            list(tool(QwenImage2ImageTool)._invoke({'prompt':'p','images':[b'x'],'prompt_extend_mode':'agent'}))
            post.assert_not_called()

    def test_translation_poll_host(self):
        from tools.qwen_image_translate import QwenImageTranslateTool
        with patch('tools.qwen_image_translate.requests.get', return_value=response({'output':{'task_status':'SUCCEEDED'}})) as get:
            result = tool(QwenImageTranslateTool)._check_task_status('id', 'test-key')
            self.assertEqual(result['output']['task_status'], 'SUCCEEDED')
            self.assertEqual(get.call_args.args[0], HOST+'/api/v1/tasks/id')

    def test_qwen_multiple_images_in_one_choice(self):
        data={'output':{'choices':[{'message':{'content':[{'image':'https://x/1.png'},{'image':'https://x/2.png'}]}}]}}
        with patch('tools.qwen_text_2_image.requests.post', return_value=response(data)):
            messages=list(tool(QwenText2ImageTool)._invoke({'prompt':'p','n':2}))
            self.assertIn('1.png',str(messages))
            self.assertIn('2.png',str(messages))

    def test_sizes(self):
        self.assertTrue(WanText2ImageTool._is_valid_size('wan2.6-t2i','768*2700',False))
        self.assertFalse(WanText2ImageTool._is_valid_size('wan2.6-t2i','2K',False))
        self.assertTrue(QwenImage2ImageTool._is_size_valid_for_model('qwen-image-3.0','2048*2048'))
        self.assertFalse(QwenImage2ImageTool._is_size_valid_for_model('qwen-image-3.0','256*8192'))


if __name__ == '__main__':
    unittest.main()
