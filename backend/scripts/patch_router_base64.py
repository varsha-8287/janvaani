with open('backend/app/speech/router.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '"application/octet-stream",',
    '"application/octet-stream",\n    "application/json",'
)

old_body = '''    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="Audio body is empty.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio exceeds the 10 MB limit.")

    wav_audio = _convert_to_wav_16k(audio)'''

new_body = '''    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(status_code=400, detail="Audio body is empty.")
    if len(raw_body) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio exceeds the 10 MB limit.")

    if content_type == "application/json":
        try:
            import json
            payload = json.loads(raw_body)
            b64_str = payload.get("audio_base64") or payload.get("audio") or ""
            audio = base64.b64decode(b64_str)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Could not parse base64 audio payload.") from exc
    else:
        audio = raw_body

    wav_audio = _convert_to_wav_16k(audio)'''

if old_body in text:
    text = text.replace(old_body, new_body)
elif old_body.replace('\n', '\r\n') in text:
    text = text.replace(old_body.replace('\n', '\r\n'), new_body.replace('\n', '\r\n'))
else:
    print('Could not find old_body in router.py!')

with open('backend/app/speech/router.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated router.py with base64 support')

