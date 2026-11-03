with open('backend/app/speech/router.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_block = '''        for item in output:
            if isinstance(item, dict):
                text = item.get("source")
                if isinstance(text, str) and text.strip():
                    return text.strip()

    raise HTTPException(
        status_code=502,
        detail="Speech provider did not return recognized text.",
    )'''

new_block = '''        for item in output:
            if isinstance(item, dict):
                text = item.get("source")
                if isinstance(text, str):
                    return text.strip()

    return ""'''

# Handle both CRLF and LF
if old_block in text:
    text = text.replace(old_block, new_block)
elif old_block.replace('\n', '\r\n') in text:
    text = text.replace(old_block.replace('\n', '\r\n'), new_block.replace('\n', '\r\n'))
else:
    print('Target block not found!')

with open('backend/app/speech/router.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated speech router successfully')

