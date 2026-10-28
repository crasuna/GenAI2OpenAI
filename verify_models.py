"""One short non-streaming request per current text model; use local credentials."""
import sys
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from local_credentials import load_token


def main():
    root = Path(__file__).resolve().parent
    output = root / 'logs' / 'model-verification.json'
    output.parent.mkdir(exist_ok=True)
    session = requests.Session()
    session.trust_env = False
    print('Test all 7 current text models with one short request each.')
    print('GPT models are marked PAID by the school. Using local credentials when available.')
    token = load_token()
    if not token:
        print('No token entered; no requests sent.')
        return
    session.headers['Authorization'] = 'Bearer ' + token
    report = {'started_at': datetime.now().astimezone().isoformat(),
              'mode': 'non-streaming', 'status': 'running', 'checks': []}

    def save():
        temporary = output.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(output)

    try:
        response = session.get('http://127.0.0.1:5057/v1/models', timeout=10)
        response.raise_for_status()
        models = [row['id'] for row in response.json()['data']]
        report['models'] = models
        save()
        for model in models:
            print('Testing:', model, flush=True)
            started = time.monotonic()
            check = {'model': model, 'passed': False}
            try:
                response = session.post('http://127.0.0.1:5057/v1/chat/completions',
                    json={'model': model, 'messages': [{'role': 'user',
                          'content': 'Reply with exactly: API_OK'}],
                          'stream': False, 'max_tokens': 256}, timeout=(10, 90))
                check['http_status'] = response.status_code
                data = response.json()
                if response.ok and isinstance(data, dict) and data.get('choices'):
                    content = data['choices'][0].get('message', {}).get('content')
                    check['has_text'] = isinstance(content, str) and bool(content.strip())
                    check['passed'] = check['has_text'] and 'API_OK' in content
                    check['finish_reason'] = data['choices'][0].get('finish_reason')
                    check['reply'] = content.replace(token, '[REDACTED]')[:300] if isinstance(content, str) else None
                else:
                    # Only store a bounded error field, never request headers or exceptions.
                    error = data.get('error', 'No choices in response') if isinstance(data, dict) else 'Invalid response shape'
                    check['error'] = str(error).replace(token, '[REDACTED]')[:500]
            except Exception as exc:
                check['error_type'] = type(exc).__name__
            check['seconds'] = round(time.monotonic() - started, 2)
            report['checks'].append(check)
            save()
            print('PASS' if check['passed'] else 'FAIL', model, check['seconds'], 'seconds', flush=True)
        report['status'] = 'complete'
    except Exception as exc:
        report['status'] = 'failed'
        report['error_type'] = type(exc).__name__
    finally:
        report['finished_at'] = datetime.now().astimezone().isoformat()
        save()
        session.headers.pop('Authorization', None)
        session.close()
        token = ''
    print('Results:', output)
    if sys.stdin.isatty():
        try:
            input('Press Enter to close...')
        except EOFError:
            pass


if __name__ == '__main__':
    main()
