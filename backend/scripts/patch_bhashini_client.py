with open('backend/app/speech/bhashini_client.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'IIT_MADRAS_PIPELINE_ID,\n    PIPELINE_CONFIG_URL,',
    'DEFAULT_BHASHINI_PIPELINE_ID,\n    IIT_MADRAS_PIPELINE_ID,\n    PIPELINE_CONFIG_URL,'
)
text = text.replace(
    '"pipelineId": IIT_MADRAS_PIPELINE_ID,',
    '"pipelineId": DEFAULT_BHASHINI_PIPELINE_ID,'
)
with open('backend/app/speech/bhashini_client.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated bhashini_client.py')

