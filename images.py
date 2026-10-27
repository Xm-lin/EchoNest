"""Provider adapter: expects JSON with images[0].url / data[0].url / base64 image.
Agens API response schema must be checked against provider documentation before production use.
"""
import base64
import io
from urllib.parse import quote
import aiohttp
from PIL import Image
import config

class ImageProviderError(RuntimeError):
    pass

async def create_image(prompt):
    if not (config.IMAGE_API_URL and config.IMAGE_API_KEY):
        raise ImageProviderError('尚未設定 IMAGE_API_URL 或 IMAGE_API_KEY')
    headers={'Authorization':f'Bearer {config.IMAGE_API_KEY}'}
    payload={'prompt':prompt[:1500], 'size':'1024x1024', 'n':1, 'return_base64':True}
    payload['model']=config.IMAGE_MODEL or 'agnes-image-2.1-flash'
    timeout=aiohttp.ClientTimeout(total=100)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(config.IMAGE_API_URL,json=payload,headers=headers) as r:
            if r.status not in (200,201,202):
                raise ImageProviderError(f'圖片 API HTTP {r.status}')
            data=await r.json()
        item=(data.get('data') or data.get('images') or [data])
        if isinstance(item,dict): item=[item]
        first=item[0]
        if isinstance(first,str):
            url=first
        else:
            url=first.get('url') or first.get('image_url')
            raw=first.get('b64_json') or first.get('base64')
            if raw:
                return validate_image(base64.b64decode(raw))
        if not url or not url.startswith('https://'):
            raise ImageProviderError('API 回應格式不符合目前圖片介面；請提供服務商文件')
        # Prevent arbitrary URL fetches from untrusted provider response.
        if not url.split('/')[2].lower().endswith(('agnes-ai.com','agnes.ai','supabase.co','googleusercontent.com','googleapis.com','cloudfront.net')):
            raise ImageProviderError('圖片來源網域未在允許清單，請確認服務商文件')
        async with session.get(url) as r:
            if r.status!=200: raise ImageProviderError(f'下載圖片失敗 HTTP {r.status}')
            return validate_image(await r.read())

def validate_image(data):
    if len(data)>12*1024*1024: raise ImageProviderError('圖片超過 12MB')
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.thumbnail((1024,1024))
            out=io.BytesIO();img.convert('RGB').save(out,'PNG',optimize=True)
            return out.getvalue()
    except Exception as exc:
        raise ImageProviderError('API 未回傳有效圖片') from exc

async def upload_image(character_id, image_bytes):
    if not (config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY):
        raise ImageProviderError('Supabase Storage 環境變數未設定')
    path=f'characters/{character_id}.png'
    bucket=quote(config.SUPABASE_STORAGE_BUCKET,safe='')
    url=f'{config.SUPABASE_URL}/storage/v1/object/{bucket}/{path}'
    headers={'apikey':config.SUPABASE_SERVICE_ROLE_KEY,
             'Authorization':f'Bearer {config.SUPABASE_SERVICE_ROLE_KEY}',
             'Content-Type':'image/png','x-upsert':'true'}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=40)) as session:
        async with session.post(url,data=image_bytes,headers=headers) as r:
            if r.status not in (200,201):
                raise ImageProviderError(f'Storage 上傳失敗 HTTP {r.status}')
    return f'{config.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}'

async def delete_image(character_id):
    if not (config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY): return
    bucket=quote(config.SUPABASE_STORAGE_BUCKET,safe='')
    url=f'{config.SUPABASE_URL}/storage/v1/object/{bucket}/characters/{character_id}.png'
    headers={'apikey':config.SUPABASE_SERVICE_ROLE_KEY,
             'Authorization':f'Bearer {config.SUPABASE_SERVICE_ROLE_KEY}'}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
        async with session.delete(url,headers=headers): pass
