from __future__ import annotations

from datetime import date
from typing import Any

from database import get_daily_challenge, save_daily_challenge
from services.ai_provider import ProviderFactory


class InterviewService:
    def __init__(self, provider_name: str) -> None:
        self.provider = ProviderFactory.create(provider_name)

    def generate_questions(
        self,
        domain: str,
        difficulty: str,
        count: int,
        focus: str,
        experience_level: str = '',
        resume_text: str = '',
    ) -> list[dict[str, Any]]:
        return self.provider.generate_questions(domain, difficulty, count, focus, experience_level, resume_text)

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        domain: str,
        difficulty: str,
        experience_level: str = '',
    ) -> dict[str, Any]:
        return self.provider.evaluate_answer(question, answer, domain, difficulty, experience_level)

    def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        return self.provider.transcribe_audio(audio_bytes, filename)

    def get_daily_challenge(self, domain: str, difficulty: str) -> dict[str, Any]:
        today = date.today().isoformat()
        existing = get_daily_challenge(today, domain, difficulty)
        if existing:
            return {
                'question': existing['question_text'],
                'type': existing['question_type'],
                'topic': existing['topic'] or 'Daily Challenge',
                'tags': ['Daily Challenge', domain],
                'difficulty': difficulty,
                'domain': domain,
            }

        question = self.generate_questions(domain, difficulty, 1, 'Mixed')[0]
        save_daily_challenge(today, domain, difficulty, question)
        return question
