import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import start_local as s

class Fake:
    status_code = 200
    def iter_lines(self):
        yield b'data: ' + json.dumps({'code':500, 'errMsg':'model unavailable'}).encode()

with s.main.app.test_request_context():
    with patch.object(s.main.requests, 'post', return_value=Fake()):
        events = list(s.main.stream_genai_events([{'role':'user','content':'x'}], 'deepseek-pro', 64))
assert events == [{'type':'error','error':'model unavailable'}], events
with s.main.app.test_client() as c:
    assert c.get('/health').status_code == 200
    assert c.get('/v1/models').status_code == 401
    assert c.get('/health', headers={'Origin':'https://example.com'}).status_code == 403
print('upstream error / health / missing auth / origin checks PASS')
with s.main.app.test_client() as c:
    with patch.object(s.main, 'stream_genai_events', return_value=iter([
        {'type':'delta', 'content':'API_OK'}, {'type':'done'}])):
        r = c.post('/v1/chat/completions', headers={'Authorization':'Bearer offline'}, json={
            'model':'deepseek-pro','messages':[{'role':'user','content':'x'}],'stream':True})
        assert r.status_code == 200
        assert 'Connection' not in r.headers
        assert b'API_OK' in r.data and b'[DONE]' in r.data
        print('stream contract PASS', list(r.headers))
