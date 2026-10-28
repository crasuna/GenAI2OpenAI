# Focused public request regression: DeepSeek images must reach school payloads.
import sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import start_local as s
class Chat:
 status_code=200
 def iter_lines(self):
  yield b'data: {"choices":[{"delta":{"content":"VISION_OK"}}]}'
  yield b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}'
def image(v): return {'type':'image_url','image_url':{'url':'data:image/png;base64,'+v}}
messages=[{'role':'user','content':[{'type':'text','text':'Read both'},image('YQ=='),image('Yg==')]}]
original=json.loads(json.dumps(messages))
for model in ('deepseek-pro','deepseek-pro-search','gpt-6.1-sol'):
 for stream in (False,True):
  with patch.object(s.main,'upload_image_to_genai',side_effect=lambda data,*a:{'imageUrl':'https://example.org/'+data.decode()+'.png','width':640,'height':360}),patch.object(s.main.requests,'post',return_value=Chat()) as post,patch.object(s.main,'fetch_search_results',return_value={'links':[],'count':0}),s.main.app.test_client() as c:
   r=c.post('/v1/chat/completions',headers={'Authorization':'Bearer test'},json={'model':model,'messages':messages,'stream':stream})
   assert r.status_code==200,(model,r.status_code,r.json)
   assert b'VISION_OK' in r.data
   body=post.call_args.kwargs['json']
   assert body['imageUrls']==['https://example.org/a.png','https://example.org/b.png']
   assert body['chatInfo']=='Read both'
   assert body['messages']==[]
assert messages==original
history=messages+[{'role':'assistant','content':'OK'},{'role':'user','content':'What was on the left?'}]
with patch.object(s.main,'upload_image_to_genai',side_effect=lambda data,*a:{'imageUrl':'https://example.org/'+data.decode()+'.png'}),patch.object(s.main.requests,'post',return_value=Chat()) as post,s.main.app.test_client() as c:
 r=c.post('/v1/chat/completions',headers={'Authorization':'Bearer test'},json={'model':'deepseek-pro','messages':history})
 assert r.status_code==200
 body=post.call_args.kwargs['json']
 assert body['messages'][0]['imageUrls']==['https://example.org/a.png','https://example.org/b.png']
 assert body['imageUrls']==['https://example.org/a.png','https://example.org/b.png']
print('DeepSeek/GPT JSON+SSE, multi-image, historical images, input non-mutation PASS')
