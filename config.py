from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

APP_NAME = 'AI Interview Preparation Bot'
DB_PATH = os.getenv('DB_PATH', str(BASE_DIR / 'interview_bot.db'))
UPLOAD_DIR = BASE_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
OPENAI_TRANSCRIPTION_MODEL = os.getenv('OPENAI_TRANSCRIPTION_MODEL', 'gpt-4o-mini-transcribe')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

DEFAULT_PROVIDER = os.getenv('DEFAULT_PROVIDER', 'demo').lower()
AVAILABLE_PROVIDERS = ['demo']
if OPENAI_API_KEY:
    AVAILABLE_PROVIDERS.append('openai')
if GEMINI_API_KEY:
    AVAILABLE_PROVIDERS.append('gemini')
if DEFAULT_PROVIDER not in AVAILABLE_PROVIDERS:
    DEFAULT_PROVIDER = AVAILABLE_PROVIDERS[0]

SUPPORTED_DOMAINS = [
    'Software Engineer',
    'Data Analyst',
    'ML Engineer',
    'Web Developer',
    'Backend Developer',
    'Frontend Developer',
    'DevOps Engineer',
    'QA Engineer',
    'Product Analyst',
]

DIFFICULTY_LEVELS = ['Easy', 'Medium', 'Hard']
QUESTION_FOCUS = ['Technical', 'HR', 'Mixed']
EXPERIENCE_LEVELS = ['Fresher', '0-2 Years', '2-5 Years', '5+ Years']
DEFAULT_TIME_LIMIT_SECONDS = 120
