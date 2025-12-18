import os
from openai import OpenAI
from google.cloud import texttospeech
from dotenv import load_dotenv

load_dotenv()

from typing import Iterator

class TTSService:
    def generate_speech(self, text: str) -> Iterator[bytes]:
        raise NotImplementedError

class OpenAITTSService(TTSService):
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_speech(self, text: str) -> Iterator[bytes]:
        if not os.getenv("OPENAI_API_KEY"):
            raise Exception("OPENAI_API_KEY not found")
            
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text
            )
            # Stream the response
            return response.iter_bytes()
        except Exception as e:
            print(f"Error generating OpenAI speech: {e}")
            raise e

class GoogleTTSService(TTSService):
    def __init__(self):
        # Assumes GOOGLE_APPLICATION_CREDENTIALS is set in env
        self.client = texttospeech.TextToSpeechClient()

    def generate_speech(self, text: str) -> Iterator[bytes]:
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Build the voice request, select the language code ("en-US") and the ssml
            # voice gender ("neutral")
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Wavenet-D", # Standard WaveNet voice
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )

            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # Google TTS returns full content, so we yield it as a single chunk
            yield response.audio_content
        except Exception as e:
            print(f"Error generating Google speech: {e}")
            raise e

def get_tts_service(tier: str = "free") -> TTSService:
    if tier == "premium":
        return OpenAITTSService()
    else:
        return GoogleTTSService()
