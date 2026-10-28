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
    assert len(ids) == len(set(ids)) == 8
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

# Merge leading system policies in order and append the text transport contract.
client_messages = [
    {'role': 'system', 'content': 'Client policy A.'},
    {'role': 'system', 'content': 'Client policy B.'},
    {'role': 'user', 'content': 'Read check.txt.'},
]
original_messages = json.loads(json.dumps(client_messages))
tool_definitions = [{'type': 'function', 'function': {'name': 'read',
    'description': 'Read a test file.', 'parameters': {'type': 'object',
    'properties': {'file_path': {'type': 'string'}}, 'required': ['file_path']}}}]
combined = s.main.build_tool_calling_messages(client_messages, tool_definitions, 'auto')
assert [m['role'] for m in combined] == ['system', 'user']
assert 'Client policy A.\n\nClient policy B.\n\nTRANSPORT REQUIREMENT:' in combined[0]['content']
assert 'Native function/tool calling is DISABLED' in combined[0]['content']
assert 'ordinary visible assistant final-answer text' in combined[0]['content']
assert 'TOOL_REQUEST' in combined[0]['content']
assert combined[1:] == client_messages[2:]
assert client_messages == original_messages
plain = [{'role': 'user', 'content': 'Read check.txt.'}]
required = s.main.build_tool_calling_messages(plain, tool_definitions, 'required')
assert required[1:] == plain
assert 'Native function/tool calling is DISABLED' in required[0]['content']
assert '"required"' in required[0]['content']
parsed = s.main.parse_tool_calls_from_content('TOOL_REQUEST {"tool_calls":[{"name":"read","arguments":{"file_path":"check.txt"}}]}')
assert parsed[0]['function']['name'] == 'read'
assert json.loads(parsed[0]['function']['arguments']) == {'file_path': 'check.txt'}
print('merged system policies / text transport / non-mutation / prefixed parsing PASS')

# Do not disguise an empty upstream completion as a successful tool response.
with s.main.app.test_client() as c:
    for stream in (False, True):
        with patch.object(s.main, 'stream_genai_events', return_value=iter([
            {'type': 'delta', 'content': ''}, {'type': 'done'}])):
            r = c.post('/v1/chat/completions', headers={'Authorization': 'Bearer offline'}, json={
                'model': 'deepseek-pro', 'messages': plain, 'tools': tool_definitions, 'stream': stream})
            assert r.status_code >= 500
            assert 'GenAI upstream returned an empty response' in r.get_data(as_text=True)
print('empty upstream tool response / stream and non-stream error PASS')

# History uses the same textual envelope as new requests, preserving IDs and objects.
call_history = [
    {'role': 'assistant', 'content': None, 'tool_calls': [
        {'id': 'call_read', 'type': 'function', 'function': {'name': 'read', 'arguments': json.dumps({'file_path': 'C:\\test\\文件.txt'})}},
        {'id': 'call_other', 'type': 'function', 'function': {'name': 'read', 'arguments': {'file_path': 'second.txt'}}}]},
    {'role': 'tool', 'tool_call_id': 'call_read', 'content': 'verification_code=TEST'},
]
original_history = json.loads(json.dumps(call_history))
normalized = s.main.normalize_messages_for_genai(call_history)
assert normalized[0]['content'].startswith('TOOL_REQUEST ')
assert '已请求调用工具' not in normalized[0]['content']
payload = json.loads(normalized[0]['content'].removeprefix('TOOL_REQUEST '))
assert payload['tool_calls'][0] == {'id': 'call_read', 'name': 'read', 'arguments': {'file_path': 'C:\\test\\文件.txt'}}
reparsed = s.main.parse_tool_calls_from_content(normalized[0]['content'])
assert [c['id'] for c in reparsed] == ['call_read', 'call_other']
assert json.loads(reparsed[1]['function']['arguments']) == {'file_path': 'second.txt'}
assert 'call_read' in normalized[1]['content'] and 'verification_code=TEST' in normalized[1]['content']
assert call_history == original_history
with_text = dict(call_history[0], content='Reading files.')
assert s.main.normalize_messages_for_genai([with_text])[0]['content'].startswith('Reading files.\nTOOL_REQUEST ')
try:
    s.main.normalize_messages_for_genai([{'role': 'assistant', 'tool_calls': [{'function': {'name': 'read', 'arguments': 'not JSON'}}]}])
except ValueError:
    pass
else:
    raise AssertionError('Invalid history arguments must not be silently rewritten')
print('canonical tool history / IDs / arguments / result linkage / non-mutation PASS')

# Search alias uses the same upstream model, with a nonempty query and references.
class SearchChat:
    status_code = 200
    def iter_lines(self):
        yield b'data: {"choices":[{"delta":{"content":"Answer with https://example.org"}}]}'
        yield b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}'
class SearchRefs:
    def raise_for_status(self): pass
    def json(self): return {'success': True, 'result': {'links': [{'link': 'https://example.org', 'title': 'Example'}], 'count': 1}}
search_messages = [{'role': 'system', 'content': 'Be brief.'}, {'role': 'user', 'content': 'Find example.'}, {'role': 'user', 'content': 'Give sources.'}]
search_original = json.loads(json.dumps(search_messages))
with s.main.app.test_client() as c:
    for stream in (False, True):
        with patch.object(s.main.requests, 'post', side_effect=[SearchChat(), SearchRefs()]) as post:
            r = c.post('/v1/chat/completions', headers={'Authorization': 'Bearer offline'}, json={'model': 'deepseek-pro-search', 'messages': search_messages, 'stream': stream})
            assert r.status_code == 200 and b'https://example.org' in r.data and b'search_results' in r.data
            body = post.call_args_list[0].kwargs['json']
            assert body['aiType'] == 'deepseek-pro' and body['netGo'] is True
            assert body['chatInfo'] == 'Find example.\n\nGive sources.'
            assert body['messages'] == search_messages[:1]
            assert post.call_args_list[1].args[0] == s.main.GENAI_SEARCH_URL
            if stream: assert b'[DONE]' in r.data
            else: assert r.json['search_results']['count'] == 1
    with patch.object(s.main.requests, 'post', return_value=SearchChat()) as post:
        r=c.post('/v1/chat/completions', headers={'Authorization': 'Bearer offline'}, json={'model':'deepseek-pro','messages':search_messages})
        assert r.status_code==200 and post.call_count==1
        assert 'netGo' not in post.call_args.kwargs['json']
        assert 'search_results' not in r.json
assert search_messages == search_original
with patch.object(s.main.requests, 'post', side_effect=s.main.requests.Timeout):
    assert 'error' in s.main.fetch_search_results({}, 'offline')
print('search alias / query split / references JSON and SSE / normal unchanged PASS')

# Search and local tools share one agent loop; only search executes in the proxy.
def collected_text(text, sources=None):
    return {'content': text, 'reasoning_content': '', 'search_results': sources}
search_call = json.dumps({'tool_calls': [{'name': 'web_search', 'arguments': {'queries': ['school official website']}}]})
local_call = json.dumps({'tool_calls': [{'name': 'write', 'arguments': {'file_path': 'report.txt', 'content': 'https://example.org'}}]})
local_tools = [{'type':'function','function':{'name':'write','parameters':{'type':'object'}}}]
with s.main.app.test_client() as c:
    for streaming in (False, True):
        with patch.object(s.main, 'collect_genai_response', side_effect=[
            collected_text(search_call), collected_text('School source: https://example.org', {'links':[{'link':'https://example.org'}], 'count':1}), collected_text(local_call)]) as collect:
            r=c.post('/v1/chat/completions',headers={'Authorization':'Bearer offline'},json={
                'model':'deepseek-pro-search','messages':[{'role':'user','content':'Search and write a report.'}],
                'tools':local_tools,'stream':streaming})
            assert r.status_code==200 and b'write' in r.data and b'https://example.org' in r.data
            assert [call.args[1] for call in collect.call_args_list] == ['deepseek-pro','deepseek-pro-search','deepseek-pro']
            assert collect.call_args_list[1].args[0] == [{'role':'user','content':'school official website'}]
            followup=collect.call_args_list[2].args[0]
            assert any('School source: https://example.org' in m['content'] for m in followup)
            if not streaming:
                message=r.json['choices'][0]['message']
                assert message['tool_calls'][0]['function']['name']=='write'
                assert 'https://example.org' in message['content']
            else: assert b'[DONE]' in r.data
    with patch.object(s.main,'collect_genai_response',return_value=collected_text(local_call)) as collect:
        r=c.post('/v1/chat/completions',headers={'Authorization':'Bearer offline'},json={
            'model':'deepseek-pro-search','messages':[{'role':'user','content':'Write a file.'}],
            'tools':local_tools,'tool_choice':{'type':'function','function':{'name':'write'}}})
        assert r.status_code==200 and collect.call_count==1
    with patch.object(s.main,'collect_genai_response',return_value=collected_text(search_call)) as collect:
        # Every search result is mocked too; repeated model searches must terminate.
        try:
            s.main.collect_search_agent_response([{'role':'user','content':'Search'}],local_tools,'auto',64,'offline',None)
        except RuntimeError as e:
            assert 'limit' in str(e)
        else: raise AssertionError('Search loop must be bounded')
print('school search + local tools / search context retention / named local tool / loop bound PASS')
