#!/usr/bin/env python3
import json, os, urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
transcript = (root / 'data/transcripts/100-alexander-fridman.md').read_text(encoding='utf-8', errors='replace')
skill = (root / 'data/digests/skills/no-ai-slop/SKILLS.md').read_text(encoding='utf-8', errors='replace')
reference = (root / 'data/digests/496-ffmpeg.md').read_text(encoding='utf-8', errors='replace')

system = '''You are editing one Lex Fridman Podcast digest for a repository. Read the full transcript, not just the title. Produce factual, compact, specific prose that a technically sophisticated reader can trust. Do not invent details or current facts. Do not identify a speaker unless the transcript clearly labels them. Avoid AI-writing tics and generic filler. The supplied no-AI-slop guide is binding. Match the editorial density and specificity of the reference digest, but do not copy its wording. Return JSON only.'''
user = f'''EPISODE: #100 – Alexander Fridman: My Dad, the Plasma Physicist\nGUEST: Alexander Fridman\n\nNO-AI-SLOP GUIDE:\n{skill}\n\nREFERENCE DIGEST (#496; use only for style/format expectations):\n{reference}\n\nFULL TRANSCRIPT:\n{transcript}\n\nReturn exactly this JSON shape:\n{{\n  "topics": [8 short specific topic strings],\n  "one_liner": "1 strong sentence, 25-45 words",\n  "summary": ["paragraph 1, 120-180 words", "paragraph 2, 120-180 words", "optional paragraph 3, 80-150 words"],\n  "takeaways": [\n    {{"heading":"specific claim, no colon, <=14 words", "body":"2-4 specific sentences grounded in transcript"}},\n    ... 5 to 7 total\n  ]\n}}\nDo not include Highlights or Chapters. Do not quote long transcript passages. Do not mention that you are summarizing a transcript.'''

payload = {
  'model': 'openai/gpt-4.1',
  'messages': [
    {'role': 'system', 'content': system},
    {'role': 'user', 'content': user},
  ],
  'temperature': 0.2,
  'max_tokens': 4000,
  'response_format': {'type': 'json_object'},
}
req = urllib.request.Request(
    'https://models.github.ai/inference/chat/completions',
    data=json.dumps(payload).encode('utf-8'),
    headers={
      'Accept': 'application/vnd.github+json',
      'Authorization': f"Bearer {os.environ['GITHUB_TOKEN']}",
      'X-GitHub-Api-Version': '2026-03-10',
      'Content-Type': 'application/json',
    },
    method='POST',
)
with urllib.request.urlopen(req, timeout=180) as r:
    response = json.load(r)
content = response['choices'][0]['message']['content']
obj = json.loads(content)
out = root / '.digest-build/model-test-100.json'
out.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(out)
