"""Malformed tool envelopes must never become successful chat responses."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import start_local as s

# Same missing closing brace as the observed pwsh response; synthetic arguments.
bad = 'TOOL_REQUEST {"tool_calls":[{"name":"read","arguments":{"file_path":"sample.txt"},"id":"test"}]'
good = 'TOOL_REQUEST {"tool_calls":[{"name":"read","arguments":{"file_path":"sample.txt"}}]}'
tools = [{'type': 'function', 'function': {'name': 'read', 'parameters': {'type': 'object'}}}]

def result(text):
    return {'content': text, 'reasoning_content': ''}

with s.main.app.test_client() as client:
    for model in ('deepseek-pro', 'deepseek-pro-search'):
        for stream in (False, True):
            body = {'model': model, 'messages': [{'role': 'user', 'content': 'Read sample.txt'}],
                    'tools': tools, 'stream': stream}
            with patch.object(s.main, 'collect_genai_response', side_effect=[result(bad), result(good)]) as collect:
                response = client.post('/v1/chat/completions', headers={'Authorization': 'Bearer offline'}, json=body)
                assert response.status_code == 200
                assert collect.call_count == 2
                assert b'TOOL_REQUEST' not in response.data
                assert b'tool_calls' in response.data
                retry = collect.call_args_list[1].args[0]
                assert retry[-1]['role'] == 'user' and '未执行' in retry[-1]['content']
            with patch.object(s.main, 'collect_genai_response', return_value=result(bad)) as collect:
                response = client.post('/v1/chat/completions', headers={'Authorization': 'Bearer offline'}, json=body)
                assert response.status_code == 502, response.data
                assert response.json['error']['code'] == 'invalid_tool_call_format'
                assert collect.call_count == 3
                assert b'sample.txt' not in response.data
            with patch.object(s.main, 'collect_genai_response', return_value=result('Ordinary answer')) as collect:
                response = client.post('/v1/chat/completions', headers={'Authorization': 'Bearer offline'}, json=body)
                assert response.status_code == 200 and collect.call_count == 1
                assert b'Ordinary answer' in response.data
print('tool repair: ordinary/search JSON/SSE, bounded retries, explicit failure PASS')

for invalid in (
    'TOOL_REQUEST {"tool_calls":[]}',
    'TOOL_REQUEST {"tool_calls":[{"arguments":{}}]}',
    'TOOL_REQUEST {"tool_calls":[{"name":"read","arguments":"not-json"}]}',
    'TOOL_REQUEST {"tool_calls":[{"name":"read","arguments":{}},42]}',
    good + ' trailing text',
):
    try:
        s.main.validate_tool_output(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid batch must not partially execute')
assert s.main.validate_tool_output('The marker TOOL_REQUEST is used by the adapter.') == []
with patch.object(s.main, 'collect_genai_response', side_effect=[result(bad), result('Done'), result('Done')]):
    try:
        s.main.collect_tool_response([], 'deepseek-pro', 64, 'offline', None)
    except s.main.InvalidToolCallFormat:
        pass
    else:
        raise AssertionError('A repair must not silently become ordinary text')
print('invalid arguments / partial batch / trailing junk / failed repair prose PASS')
