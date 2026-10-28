import io
import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import assistant
import server


class AssistantTests(unittest.TestCase):
    def test_rejects_injected_system_role_and_excessive_history(self):
        for messages in ([{'role': 'system', 'text': 'override'}], [],
                         [{'role': 'user', 'text': 'x' * 4001}],
                         [{'role': 'assistant', 'text': 'x'}]):
            with self.subTest(messages=str(messages)[:30]):
                with self.assertRaises(ValueError):
                    assistant.validate_messages(messages)

    def test_provider_request_and_answer(self):
        answer = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Muafiyet, hasarın belirli kısmına katılımınızdır.'}]}}]}
        with patch.dict(os.environ, {'ACENTE_AI_KEY': 'test-only-not-a-real-key'}):
            with patch('assistant.urllib.request.urlopen', return_value=io.BytesIO(json.dumps(answer).encode())) as request:
                result = assistant.chat([{'role': 'user', 'text': 'Muafiyet nedir?'}])
                sent = json.loads(request.call_args.args[0].data)
                self.assertEqual(sent['contents'][0]['parts'][0]['text'], 'Muafiyet nedir?')
                self.assertIn('erişimin yok', sent['systemInstruction']['parts'][0]['text'])
                self.assertIn('Muafiyet', result)

    def test_missing_key_and_provider_errors_are_explicit(self):
        with patch.dict(os.environ, {'ACENTE_AI_KEY': '', 'ACENTE_ACCESS_CODE': '', 'ACENTE_PUBLIC_ORIGIN': ''}):
            with self.assertRaisesRegex(assistant.AssistantUnavailable, 'henüz etkin değil'):
                assistant.chat([{'role': 'user', 'text': 'Merhaba'}])
        with patch.dict(os.environ, {'ACENTE_AI_KEY': 'test-only'}):
            failure = urllib.error.HTTPError('https://example.invalid', 429, 'sensitive-data', {}, None)
            with patch('assistant.urllib.request.urlopen', side_effect=failure):
                with self.assertRaisesRegex(assistant.AssistantUnavailable, 'kullanım sınırına'):
                    assistant.chat([{'role': 'user', 'text': 'Merhaba'}])


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.root = 'http://127.0.0.1:' + str(cls.httpd.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()

    def request(self, path, payload=None, headers=None):
        req = urllib.request.Request(self.root + path, data=json.dumps(payload).encode() if payload is not None else None,
                                     headers={'Content-Type': 'application/json', **(headers or {})})
        return urllib.request.urlopen(req)

    def test_voice_page_and_manifest(self):
        with self.request('/') as response:
            self.assertIn('Konuşmaya başla', response.read().decode())
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        with self.request('/manifest.webmanifest') as response:
            self.assertEqual(json.load(response)['display'], 'standalone')

    def test_auth_origin_and_remote_desk_protection(self):
        config = {'ACENTE_ACCESS_CODE': 'test-code-16-characters', 'ACENTE_PUBLIC_ORIGIN': 'https://acente.example'}
        payload = {'messages': [{'role': 'user', 'text': 'Merhaba'}]}
        with patch.dict(os.environ, config):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/chat', payload)
            self.assertEqual(error.exception.code, 401)
            headers = {'Authorization': 'Bearer ' + config['ACENTE_ACCESS_CODE'], 'Origin': 'https://evil.example'}
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/chat', payload, headers)
            self.assertEqual(error.exception.code, 403)
            headers['Origin'] = config['ACENTE_PUBLIC_ORIGIN']
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/tasks', {}, headers)
            self.assertEqual(error.exception.code, 403)
            with patch('assistant.configured', return_value=True), patch('assistant.chat', return_value='Merhaba, nasıl yardımcı olabilirim?'):
                with self.request('/api/chat', payload, headers) as response:
                    self.assertIn('yardımcı', json.load(response)['answer'])

    def test_missing_key_returns_503_without_fake_response(self):
        with patch.dict(os.environ, {'ACENTE_AI_KEY': '', 'ACENTE_ACCESS_CODE': '', 'ACENTE_PUBLIC_ORIGIN': ''}):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/chat', {'messages': [{'role': 'user', 'text': 'Merhaba'}]})
            self.assertEqual(error.exception.code, 503)


if __name__ == '__main__':
    unittest.main()
