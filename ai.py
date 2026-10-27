import aiohttp

async def generate(api_key: str, model: str, personality: str, history: list[dict], summary: str = '') -> str:
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    prompt = ('你是 Discord 角色扮演聊天助手。保持角色一致，遵守安全規則。'
              f'角色設定：{personality[:1500]}。過往摘要：{summary[:1500]}。'
              '不同使用者的對話請勿混淆說話者。')
    contents = []
    for m in history[-20:]:
        role = 'model' if m['role'] == 'assistant' else 'user'
        contents.append({'role': role, 'parts': [{'text': m['content'][:1000]}]})
    payload = {'systemInstruction': {'parts': [{'text': prompt}]}, 'contents': contents,
               'generationConfig': {'maxOutputTokens': 500}}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, params={'key': api_key}, json=payload) as response:
            if response.status != 200:
                raise RuntimeError(f'Gemini request failed: HTTP {response.status}')
            data = await response.json()
    try:
        text = ''.join(p.get('text', '') for p in data['candidates'][0]['content']['parts'])
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError('Gemini returned no text') from exc
    if not text.strip():
        raise RuntimeError('Gemini returned empty text')
    return text[:3500]
