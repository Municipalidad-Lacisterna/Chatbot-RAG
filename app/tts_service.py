import os
import requests

def convertir_texto_a_audio(texto: str, voice_id: str = 'ErXwobaYiN019PkySvjV') -> bytes:
    api_key = 'sk_674c3bfada8f45496d7044a3a168a1663c4523f0ea25bb5c'
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    headers = {'xi-api-key': api_key, 'Content-Type': 'application/json'}
    data = {
        'text': texto,
        'model_id': 'eleven_multilingual_v2',
        'voice_settings': {
            'stability': 0.75,
            'similarity_boost': 0.75,
            'style': 0.0,
            'use_speaker_boost': True
        }
    }
    resp = requests.post(url, headers=headers, json=data, timeout=30)
    if resp.status_code == 200:
        return resp.content
    else:
        raise RuntimeError(f'Error ElevenLabs: {resp.text}')
