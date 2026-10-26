import os
import requests
from app import settings

def convertir_texto_a_audio(texto: str, voice_id: str = 'ErXwobaYiN019PkySvjV') -> bytes:
    api_key = getattr(settings, 'API_KEY', '') or getattr(settings, 'GOOGLE_API_KEY', '')
    if not api_key:
        raise ValueError('API Key no configurada')
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    headers = {'xi-api-key': api_key, 'Content-Type': 'application/json'}
    data = {
        'text': texto,
        'model_id': 'eleven_multilingual_v2',
        'voice_settings': {
            'stability': 0.40,
            'similarity_boost': 0.85,
            'style': 0.25,
            'use_speaker_boost': True
        }
    }
    resp = requests.post(url, headers=headers, json=data, timeout=30)
    if resp.status_code == 200:
        return resp.content
    else:
        raise RuntimeError(f'Error ElevenLabs: {resp.text}')
