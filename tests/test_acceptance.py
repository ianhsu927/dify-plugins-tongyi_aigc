"""Offline SDK registration and HTTP contract checks; never send real requests."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from dify_plugin.config.config import DifyPluginEnv
import requests
from dify_plugin.core.plugin_registration import PluginRegistration
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from provider.tongyi_aigc import TongyiAigcProvider
from provider.endpoints import api_url
from tools.wan_video import WanVideoTool
from tools.wan_video_query import WanVideoQueryTool
from tools.qwen_text_2_image import QwenText2ImageTool
from test_models import tool, response, HOST


class AcceptanceTest(unittest.TestCase):
    def setUp(self):
        # Fail closed if a test accidentally leaves HTTP unmocked.
        self.network = patch('requests.sessions.Session.request', side_effect=AssertionError('Unmocked HTTP'))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_sdk_registration(self):
        registration = PluginRegistration(DifyPluginEnv())
        provider, cls, mapping = registration.tools_mapping['tongyi_aigc']
        self.assertEqual(cls.__name__, TongyiAigcProvider.__name__)
        paths = yaml.safe_load(Path('provider/tongyi_aigc.yaml').read_text())['tools']
        names = [yaml.safe_load(Path(p).read_text())['identity']['name'] for p in paths]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(mapping), set(names))
        self.assertEqual(len(mapping), 19)
        self.assertEqual(mapping['wan_video'][1].__name__, mapping['wan_video_edit'][1].__name__)
        self.assertEqual(str(registration.configuration.version), '0.0.5')
        self.assertTrue(Path('_assets/icon.svg').is_file())

    def test_invalid_credentials_never_call_http(self):
        provider = TongyiAigcProvider()
        for credentials in [{}, {'api_key': 'short'}, {'api_key': 'test-key-long', 'api_base_url':'https://example.com'}]:
            with self.subTest(credentials=credentials), patch('provider.tongyi_aigc.requests.post') as post:
                with self.assertRaises(ToolProviderCredentialValidationError):
                    provider._validate_credentials(credentials)
                post.assert_not_called()

    def test_credential_probe_contract(self):
        with patch('provider.tongyi_aigc.requests.post', return_value=response({'choices':[{'message':{'content':'Hello'}}]})) as post:
            TongyiAigcProvider()._validate_credentials({'api_key':'test-key-long','api_base_url':HOST})
            self.assertEqual(post.call_args.args[0], HOST+'/compatible-mode/v1/chat/completions')
            self.assertEqual(post.call_args.kwargs['json']['model'], 'qwen-plus')
            self.assertEqual(post.call_args.kwargs['json']['max_tokens'], 8)

    def test_credential_failures(self):
        for value in [response({'error':{'message':'denied'}},401),response({'choices':[]}),response({})]:
            with self.subTest(value=value), patch('provider.tongyi_aigc.requests.post',return_value=value):
                with self.assertRaises(ToolProviderCredentialValidationError):
                    TongyiAigcProvider()._validate_credentials({'api_key':'test-key-long'})
        for error in [requests.Timeout('timeout'), requests.ConnectionError('offline'), ValueError('non-json')]:
            with patch('provider.tongyi_aigc.requests.post',side_effect=error):
                with self.assertRaises(ToolProviderCredentialValidationError):
                    TongyiAigcProvider()._validate_credentials({'api_key':'test-key-long'})

    def test_host_validation(self):
        for host in [HOST+':8443',HOST+'/x',HOST+'#x','https://user:pass@dashscope.aliyuncs.com','https://dashscope.aliyuncs.com.evil.test','https://maas.aliyuncs.com']:
            with self.subTest(host=host), self.assertRaises(ValueError):
                api_url({'api_base_url':host},'/api')
        self.assertEqual(api_url({'api_base_url':' '+HOST+'/ '},'/api'),HOST+'/api')
        self.assertEqual(api_url({'api_base_url':HOST+':443'},'/api'),HOST+':443/api')

    def test_video_lifecycle_and_download_contract(self):
        with patch('tools.wan_video.requests.post',return_value=response({'output':{'task_id':'task123','task_status':'PENDING'}})) as post:
            messages=list(tool(WanVideoTool)._invoke({'prompt':'test','duration':2,'resolution':'480P'}))
            raw=next(m.message.json_object for m in messages if m.type.value=='json')
            task_id=raw['output']['task_id']
            self.assertEqual(post.call_args.kwargs['headers']['Authorization'],'Bearer test-key')
            self.assertEqual(post.call_args.kwargs['headers']['X-DashScope-Async'],'enable')
        for status in ['PENDING','RUNNING','SUCCEEDED','FAILED','CANCELED','UNKNOWN']:
            data={'output':{'task_id':task_id,'task_status':status,'video_url':'https://cdn.example/video.mp4','code':'TaskFailed','message':'failed'}}
            with self.subTest(status=status), patch('tools.wan_video_query.requests.get',return_value=response(data)) as get:
                messages=list(tool(WanVideoQueryTool)._invoke({'task_id':task_id,'download_video':'false'}))
                self.assertIn(status,str(messages))
                self.assertEqual(get.call_count,1)
                self.assertEqual(get.call_args.args[0],HOST+'/api/v1/tasks/'+task_id)
        download=response({},200); download.content=b'test-video'
        with patch('tools.wan_video_query.requests.get',side_effect=[response({'output':{'task_status':'SUCCEEDED','video_url':'https://cdn.example/video.mp4'}}),download]) as get:
            messages=list(tool(WanVideoQueryTool)._invoke({'task_id':task_id,'download_video':'true'}))
            self.assertEqual(get.call_count,2)
            self.assertNotIn('headers',get.call_args.kwargs) # no API key on media download
            self.assertTrue(any(m.type.value=='blob' for m in messages))

    def test_video_submit_failure_and_invalid_input(self):
        for data,status in [({},200),({'code':'Denied','message':'denied'},403)]:
            with patch('tools.wan_video.requests.post',return_value=response(data,status)):
                messages=list(tool(WanVideoTool)._invoke({'prompt':'test'}))
                self.assertNotIn('视频任务已提交',str(messages))
                self.assertIn('❌',str(messages))
        with patch('tools.wan_video.requests.post') as post:
            list(tool(WanVideoTool)._invoke({'prompt':'test','duration':31}))
            post.assert_not_called()
        with patch('tools.wan_video.requests.post',side_effect=requests.Timeout('timeout')):
            self.assertIn('❌',str(list(tool(WanVideoTool)._invoke({'prompt':'test'}))))

    def test_image_failure_contract(self):
        for data,status in [({},200),({'output':{'choices':[{'message':{'content':[{'text':'no image'}]}}]}},200),({'code':'Denied'},403)]:
            with patch('tools.qwen_text_2_image.requests.post',return_value=response(data,status)):
                messages=list(tool(QwenText2ImageTool)._invoke({'prompt':'test'}))
                self.assertIn('❌',str(messages))
                self.assertNotIn('图像生成成功',str(messages))
        with patch('tools.qwen_text_2_image.requests.post') as post:
            list(tool(QwenText2ImageTool)._invoke({'prompt':' '}))
            post.assert_not_called()

    def test_readme_version_consistency(self):
        for path,marker in [('README.md','**Current Version**: v'),('readme/README_zh_Hans.md','**当前版本**: v')]:
            text=Path(path).read_text()
            self.assertIn(marker+'0.0.5',text)
            self.assertIn('api_base_url',text)
            self.assertIn('qwen-plus',text)
