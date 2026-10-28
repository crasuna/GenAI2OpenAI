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

# Verify the public model endpoint against the supplied upstream catalog.
catalog = json.loads((Path(__file__).resolve().parents[1] / 'docs/model-catalog-2026-10-28.json').read_text(encoding='utf-8'))
text_records = [r for r in catalog['records'] if r['aiType'] != 'GPT-Image-2']
with s.main.app.test_client() as c:
    r = c.get('/v1/models', headers={'Authorization': 'Bearer offline'})
    assert r.status_code == 200
    ids = [row['id'] for row in r.json['data']]
    assert len(ids) == len(set(ids)) == 7
    assert 'deepseek-pro' in ids and 'deepseek-v3' not in ids
    resolved = {s.main.resolve_model(model) for model in ids}
    assert resolved == {(row['aiType'], row['rootAiType']) for row in text_records}
    for row in text_records:
        assert s.main.resolve_model(row['aiName'].upper()) == (row['aiType'], row['rootAiType'])
    assert s.main.resolve_model('custom-model') == ('custom-model', 'xinference')
print('current catalog / routing / aliases / passthrough PASS')

# Kimi's backend appends chatInfo as a new user message: do not send it empty.
history = [{'role': 'system', 'content': 'Be brief.'},
           {'role': 'user', 'content': 'Remember BLUE.'},
           {'role': 'assistant', 'content': 'OK'},
           {'role': 'user', 'content': 'What word?'}]
original = json.loads(json.dumps(history))
with s.main.app.test_request_context():
    for model in ('kimi-k3', 'Kimi-K3'):
        with patch.object(s.main.requests, 'post', return_value=Fake()) as post:
            list(s.main.stream_genai_events(history, model, 256))
            body = post.call_args.kwargs['json']
            assert body['chatInfo'] == 'What word?', body
            assert body['messages'] == history[:-1], body
            assert body['aiType'] == 'Kimi-k3'
    assert history == original
    with patch.object(s.main.requests, 'post', return_value=Fake()) as post:
        list(s.main.stream_genai_events(history, 'deepseek-pro', 256))
        assert post.call_args.kwargs['json']['messages'] == history
print('Kimi current turn / history / non-mutation / other models PASS')
