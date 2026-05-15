from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass
from typing import Any

from config import GEMINI_API_KEY, GEMINI_MODEL, OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TRANSCRIPTION_MODEL

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

try:
    from google import genai
except Exception:  # pragma: no cover
    genai = None


FALLBACK_QUESTIONS = {
    'Software Engineer': {
        'Technical': [
            ('Explain REST and when you would choose it over GraphQL.', 'APIs'),
            ('What is database indexing and what trade-offs does it introduce?', 'Databases'),
            ('How would you design a scalable URL shortener?', 'System Design'),
            ('What is the difference between multithreading and multiprocessing?', 'Python'),
        ],
        'HR': [
            ('Tell me about a time you handled a production issue under pressure.', 'Behavioral'),
            ('How do you prioritize tasks when several deadlines collide?', 'Behavioral'),
        ],
    },
    'Data Analyst': {
        'Technical': [
            ('How do you handle missing data before building a report?', 'Data Cleaning'),
            ('Explain the difference between INNER JOIN and LEFT JOIN.', 'SQL'),
            ('Which KPIs would you track for an e-commerce dashboard?', 'Business Analytics'),
            ('How do you check whether a trend is seasonal or random?', 'Time Series'),
        ],
        'HR': [
            ('Describe a time you had to explain technical findings to a non-technical stakeholder.', 'Communication'),
            ('How do you deal with ambiguous business requirements?', 'Behavioral'),
        ],
    },
    'ML Engineer': {
        'Technical': [
            ('What is overfitting and how do you reduce it?', 'Machine Learning'),
            ('Explain precision, recall, and F1-score with an example.', 'Evaluation'),
            ('How would you deploy a model for real-time inference?', 'MLOps'),
            ('What is concept drift and how do you monitor it?', 'Model Monitoring'),
        ],
        'HR': [
            ('Tell me about a time a model underperformed and how you fixed it.', 'Behavioral'),
            ('How do you communicate model limitations to stakeholders?', 'Communication'),
        ],
    },
    'Web Developer': {
        'Technical': [
            ('What is the virtual DOM and why is it useful?', 'Frontend'),
            ('How do cookies, sessions, and JWTs differ?', 'Authentication'),
            ('What causes slow page load times and how would you debug them?', 'Performance'),
            ('Explain the difference between server-side rendering and client-side rendering.', 'Architecture'),
        ],
        'HR': [
            ('How do you respond when client feedback changes the scope late in the project?', 'Behavioral'),
            ('Describe a project where teamwork was critical to delivery.', 'Behavioral'),
        ],
    },
}

GENERIC_TOPICS = ['Problem Solving', 'Communication', 'System Design', 'Testing', 'Debugging']


@dataclass
class QuestionItem:
    question: str
    type: str
    topic: str
    tags: list[str]
    difficulty: str
    domain: str


class BaseProvider:
    name = 'base'

    def generate_questions(
        self,
        domain: str,
        difficulty: str,
        count: int,
        focus: str,
        experience_level: str = '',
        resume_text: str = '',
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        domain: str,
        difficulty: str,
        experience_level: str = '',
    ) -> dict[str, Any]:
        raise NotImplementedError

    def transcribe_audio(self, audio_bytes: bytes, filename: str, mime_type: str = 'audio/wav') -> str:
        raise NotImplementedError


class DemoProvider(BaseProvider):
    name = 'demo'

    def generate_questions(
        self,
        domain: str,
        difficulty: str,
        count: int,
        focus: str,
        experience_level: str = '',
        resume_text: str = '',
    ) -> list[dict[str, Any]]:
        bank = FALLBACK_QUESTIONS.get(domain, FALLBACK_QUESTIONS['Software Engineer'])
        question_types: list[str]
        if focus == 'Mixed':
            question_types = ['Technical', 'HR']
        else:
            question_types = [focus]

        items: list[dict[str, Any]] = []
        selected_pool: list[tuple[str, str, str]] = []
        for q_type in question_types:
            for question, topic in bank.get(q_type, []):
                selected_pool.append((question, q_type, topic))

        if resume_text:
            keywords = _extract_resume_keywords(resume_text)
            for keyword in keywords[:3]:
                selected_pool.append(
                    (
                        f'Your resume mentions {keyword}. Explain your hands-on experience and the impact you created using it.',
                        'Technical',
                        keyword,
                    )
                )

        random.shuffle(selected_pool)
        for question, q_type, topic in selected_pool[:count]:
            items.append(
                {
                    'question': question,
                    'type': q_type,
                    'topic': topic,
                    'tags': [topic, difficulty, domain],
                    'difficulty': difficulty,
                    'domain': domain,
                }
            )
        while len(items) < count:
            topic = random.choice(GENERIC_TOPICS)
            items.append(
                {
                    'question': f'How would you approach a {difficulty.lower()}-level problem involving {topic.lower()} for a {domain} role?',
                    'type': 'Technical' if focus != 'HR' else 'HR',
                    'topic': topic,
                    'tags': [topic, difficulty, domain],
                    'difficulty': difficulty,
                    'domain': domain,
                }
            )
        return items

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        domain: str,
        difficulty: str,
        experience_level: str = '',
    ) -> dict[str, Any]:
        cleaned = answer.strip()
        word_count = len(cleaned.split())
        score = 3
        if word_count > 30:
            score += 2
        if word_count > 80:
            score += 2
        if any(token in cleaned.lower() for token in ['example', 'because', 'trade-off', 'result', 'improve', 'metric']):
            score += 2
        if any(token in cleaned.lower() for token in ['i built', 'i used', 'i designed', 'i analyzed']):
            score += 1
        score = min(score, 10)

        missing_points: list[str] = []
        if word_count < 40:
            missing_points.append('Add more structure, context, and depth to the answer.')
        if 'example' not in cleaned.lower():
            missing_points.append('Include one concrete example or project story.')
        if 'result' not in cleaned.lower() and 'impact' not in cleaned.lower():
            missing_points.append('Mention the outcome, metric, or business impact.')

        confidence = 'High' if word_count > 75 else 'Medium' if word_count > 35 else 'Low'
        return {
            'score': score,
            'technical_accuracy': 'Reasonably aligned, but still needs stronger role-specific detail.' if score >= 6 else 'Partially correct, but missing technical depth and structure.',
            'communication_clarity': 'Clear flow overall.' if score >= 7 else 'Needs a more organized step-by-step explanation.',
            'confidence_level': confidence,
            'missing_points': missing_points or ['Add more role-specific keywords and concrete examples.'],
            'improved_answer': (
                'Start with a direct definition or approach, explain key steps, mention one practical example, '
                'and close with the outcome or trade-off.'
            ),
            'strengths': ['Answer addresses the question directly.', 'Response shows intent to solve the problem.'],
            'topic_tags': [domain, difficulty],
        }

    def transcribe_audio(self, audio_bytes: bytes, filename: str, mime_type: str = 'audio/wav') -> str:
        raise RuntimeError('Voice transcription needs an AI provider key. Add an OpenAI key to enable speech-to-text.')


class OpenAIProvider(DemoProvider):
    name = 'openai'

    def __init__(self) -> None:
        if OpenAI is None:
            raise RuntimeError('OpenAI SDK is not installed.')
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def _response_text(self, prompt: str) -> str:
        response = self.client.responses.create(model=OPENAI_MODEL, input=prompt)
        return getattr(response, 'output_text', '') or ''

    def generate_questions(
        self,
        domain: str,
        difficulty: str,
        count: int,
        focus: str,
        experience_level: str = '',
        resume_text: str = '',
    ) -> list[dict[str, Any]]:
        prompt = f'''
You are an expert interview coach.
Generate {count} interview questions for the role: {domain}.
Difficulty: {difficulty}
Question focus: {focus}
Experience level: {experience_level or 'Not specified'}
Resume context: {resume_text[:3500] if resume_text else 'None'}
Return strict JSON with this shape:
{{
  "questions": [
    {{"question": "...", "type": "Technical or HR", "topic": "...", "tags": ["...", "..."]}}
  ]
}}
Do not add markdown. Keep each question specific and interview-grade.
        '''
        text = self._response_text(prompt)
        parsed = _safe_json_loads(text)
        questions = parsed.get('questions', []) if isinstance(parsed, dict) else []
        if not questions:
            return super().generate_questions(domain, difficulty, count, focus, experience_level, resume_text)
        return [_normalize_question(item, domain, difficulty) for item in questions[:count]]

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        domain: str,
        difficulty: str,
        experience_level: str = '',
    ) -> dict[str, Any]:
        prompt = f'''
You are a senior interviewer evaluating a candidate answer.
Role: {domain}
Difficulty: {difficulty}
Experience level: {experience_level or 'Not specified'}
Question: {question}
Candidate answer: {answer}
Return strict JSON:
{{
  "score": 0-10,
  "technical_accuracy": "...",
  "communication_clarity": "...",
  "confidence_level": "Low/Medium/High",
  "missing_points": ["..."],
  "improved_answer": "...",
  "strengths": ["..."],
  "topic_tags": ["..."]
}}
Assess confidence from wording, structure, and decisiveness. Do not use markdown.
        '''
        text = self._response_text(prompt)
        parsed = _safe_json_loads(text)
        if not isinstance(parsed, dict) or 'score' not in parsed:
            return super().evaluate_answer(question, answer, domain, difficulty, experience_level)
        parsed['score'] = max(0, min(10, float(parsed.get('score', 0))))
        return parsed

    def transcribe_audio(self, audio_bytes: bytes, filename: str, mime_type: str = 'audio/wav') -> str:
        import io

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename
        transcript = self.client.audio.transcriptions.create(
            model=OPENAI_TRANSCRIPTION_MODEL,
            file=audio_file,
        )
        return getattr(transcript, 'text', '').strip()


class GeminiProvider(DemoProvider):
    name = 'gemini'

    def __init__(self) -> None:
        if genai is None:
            raise RuntimeError('Google GenAI SDK is not installed.')
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def _generate_text(self, prompt: str) -> str:
        response = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return getattr(response, 'text', '') or ''

    def generate_questions(
        self,
        domain: str,
        difficulty: str,
        count: int,
        focus: str,
        experience_level: str = '',
        resume_text: str = '',
    ) -> list[dict[str, Any]]:
        prompt = f'''
Generate {count} interview questions for {domain}.
Difficulty: {difficulty}
Question focus: {focus}
Experience level: {experience_level or 'Not specified'}
Resume context: {resume_text[:3500] if resume_text else 'None'}
Return JSON only using this schema:
{{"questions": [{{"question": "...", "type": "Technical or HR", "topic": "...", "tags": ["...", "..."]}}]}}
        '''
        text = self._generate_text(prompt)
        parsed = _safe_json_loads(text)
        questions = parsed.get('questions', []) if isinstance(parsed, dict) else []
        if not questions:
            return super().generate_questions(domain, difficulty, count, focus, experience_level, resume_text)
        return [_normalize_question(item, domain, difficulty) for item in questions[:count]]

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        domain: str,
        difficulty: str,
        experience_level: str = '',
    ) -> dict[str, Any]:
        prompt = f'''
Evaluate this interview answer for role {domain}.
Question: {question}
Answer: {answer}
Difficulty: {difficulty}
Experience level: {experience_level or 'Not specified'}
Return JSON only:
{{
  "score": 0-10,
  "technical_accuracy": "...",
  "communication_clarity": "...",
  "confidence_level": "Low/Medium/High",
  "missing_points": ["..."],
  "improved_answer": "...",
  "strengths": ["..."],
  "topic_tags": ["..."]
}}
        '''
        text = self._generate_text(prompt)
        parsed = _safe_json_loads(text)
        if not isinstance(parsed, dict) or 'score' not in parsed:
            return super().evaluate_answer(question, answer, domain, difficulty, experience_level)
        parsed['score'] = max(0, min(10, float(parsed.get('score', 0))))
        return parsed


class ProviderFactory:
    @staticmethod
    def create(provider_name: str) -> BaseProvider:
        provider_name = (provider_name or 'demo').lower()
        if provider_name == 'openai' and OPENAI_API_KEY:
            return OpenAIProvider()
        if provider_name == 'gemini' and GEMINI_API_KEY:
            return GeminiProvider()
        return DemoProvider()


def _safe_json_loads(text: str) -> dict[str, Any] | list[Any] | dict:
    if not text:
        return {}
    stripped = text.strip()
    if stripped.startswith('```'):
        stripped = re.sub(r'^```(?:json)?|```$', '', stripped, flags=re.MULTILINE).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', stripped, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def _normalize_question(item: dict[str, Any], domain: str, difficulty: str) -> dict[str, Any]:
    return {
        'question': item.get('question', 'No question returned.'),
        'type': item.get('type', 'Technical'),
        'topic': item.get('topic', 'General'),
        'tags': item.get('tags', []) or ['Interview'],
        'difficulty': difficulty,
        'domain': domain,
    }


def _extract_resume_keywords(resume_text: str) -> list[str]:
    lines = [line.strip('•- ') for line in resume_text.splitlines() if line.strip()]
    candidates: list[str] = []
    for line in lines:
        if any(keyword in line.lower() for keyword in ['python', 'sql', 'aws', 'excel', 'power bi', 'machine learning', 'react', 'flask', 'streamlit', 'docker']):
            candidates.append(line[:60])
    return candidates[:8]
