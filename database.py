from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable

from config import DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executescript(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                target_role TEXT,
                experience_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS resume_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS interview_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_type TEXT NOT NULL,
                domain TEXT,
                difficulty TEXT,
                question_focus TEXT,
                total_questions INTEGER DEFAULT 0,
                status TEXT DEFAULT 'in_progress',
                source_resume_id INTEGER,
                avg_score REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (source_resume_id) REFERENCES resume_uploads(id)
            );

            CREATE TABLE IF NOT EXISTS question_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT,
                domain TEXT,
                difficulty TEXT,
                topic TEXT,
                topic_tags TEXT,
                user_answer TEXT,
                transcribed_answer TEXT,
                score REAL DEFAULT 0,
                technical_accuracy TEXT,
                communication_clarity TEXT,
                confidence_level TEXT,
                missing_points TEXT,
                improved_answer TEXT,
                strengths TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES interview_sessions(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS favorite_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                domain TEXT,
                difficulty TEXT,
                question_type TEXT,
                topic TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, question_text),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS daily_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_date TEXT NOT NULL,
                domain TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT DEFAULT 'Technical',
                topic TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (challenge_date, domain, difficulty)
            );
            '''
        )


def fetch_one(query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(query, tuple(params)).fetchone()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(query, tuple(params)).fetchall()


def execute(query: str, params: Iterable[Any] = ()) -> int:
    with get_connection() as conn:
        cursor = conn.execute(query, tuple(params))
        return cursor.lastrowid


def create_user(name: str, email: str, password_hash: str, target_role: str, experience_level: str) -> int:
    return execute(
        '''
        INSERT INTO users (name, email, password_hash, target_role, experience_level)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (name, email.lower().strip(), password_hash, target_role, experience_level),
    )


def get_user_by_email(email: str):
    return fetch_one('SELECT * FROM users WHERE email = ?', (email.lower().strip(),))


def get_user_by_id(user_id: int):
    return fetch_one('SELECT * FROM users WHERE id = ?', (user_id,))


def update_user_profile(user_id: int, name: str, target_role: str, experience_level: str) -> None:
    execute(
        'UPDATE users SET name = ?, target_role = ?, experience_level = ? WHERE id = ?',
        (name, target_role, experience_level, user_id),
    )


def save_resume(user_id: int, filename: str, extracted_text: str) -> int:
    return execute(
        'INSERT INTO resume_uploads (user_id, filename, extracted_text) VALUES (?, ?, ?)',
        (user_id, filename, extracted_text),
    )


def get_latest_resume(user_id: int):
    return fetch_one(
        'SELECT * FROM resume_uploads WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1',
        (user_id,),
    )


def get_resume_by_id(resume_id: int):
    return fetch_one('SELECT * FROM resume_uploads WHERE id = ?', (resume_id,))


def create_session(
    user_id: int,
    session_type: str,
    domain: str,
    difficulty: str,
    question_focus: str,
    total_questions: int,
    source_resume_id: int | None = None,
) -> int:
    return execute(
        '''
        INSERT INTO interview_sessions
        (user_id, session_type, domain, difficulty, question_focus, total_questions, source_resume_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (user_id, session_type, domain, difficulty, question_focus, total_questions, source_resume_id),
    )


def complete_session(session_id: int, avg_score: float) -> None:
    execute(
        '''
        UPDATE interview_sessions
        SET status = 'completed', avg_score = ?, completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''',
        (round(avg_score, 2), session_id),
    )


def save_attempt(
    session_id: int,
    user_id: int,
    question: dict[str, Any],
    user_answer: str,
    transcribed_answer: str,
    evaluation: dict[str, Any],
) -> int:
    return execute(
        '''
        INSERT INTO question_attempts (
            session_id, user_id, question_text, question_type, domain, difficulty, topic, topic_tags,
            user_answer, transcribed_answer, score, technical_accuracy, communication_clarity,
            confidence_level, missing_points, improved_answer, strengths
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            session_id,
            user_id,
            question.get('question', ''),
            question.get('type', 'Technical'),
            question.get('domain', ''),
            question.get('difficulty', ''),
            question.get('topic', ''),
            json.dumps(question.get('tags', [])),
            user_answer,
            transcribed_answer,
            float(evaluation.get('score', 0)),
            evaluation.get('technical_accuracy', ''),
            evaluation.get('communication_clarity', ''),
            evaluation.get('confidence_level', ''),
            json.dumps(evaluation.get('missing_points', [])),
            evaluation.get('improved_answer', ''),
            json.dumps(evaluation.get('strengths', [])),
        ),
    )


def get_user_sessions(user_id: int):
    return fetch_all(
        'SELECT * FROM interview_sessions WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,),
    )


def get_user_attempts(user_id: int):
    return fetch_all(
        'SELECT * FROM question_attempts WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,),
    )


def save_favorite_question(user_id: int, question: dict[str, Any]) -> None:
    execute(
        '''
        INSERT OR IGNORE INTO favorite_questions
        (user_id, question_text, domain, difficulty, question_type, topic)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (
            user_id,
            question.get('question', ''),
            question.get('domain', ''),
            question.get('difficulty', ''),
            question.get('type', ''),
            question.get('topic', ''),
        ),
    )


def delete_favorite_question(favorite_id: int, user_id: int) -> None:
    execute('DELETE FROM favorite_questions WHERE id = ? AND user_id = ?', (favorite_id, user_id))


def get_favorite_questions(user_id: int):
    return fetch_all(
        'SELECT * FROM favorite_questions WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,),
    )


def get_daily_challenge(challenge_date: str, domain: str, difficulty: str):
    return fetch_one(
        '''
        SELECT * FROM daily_challenges
        WHERE challenge_date = ? AND domain = ? AND difficulty = ?
        ''',
        (challenge_date, domain, difficulty),
    )


def save_daily_challenge(challenge_date: str, domain: str, difficulty: str, question: dict[str, Any]) -> int:
    return execute(
        '''
        INSERT OR IGNORE INTO daily_challenges
        (challenge_date, domain, difficulty, question_text, question_type, topic)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (
            challenge_date,
            domain,
            difficulty,
            question.get('question', ''),
            question.get('type', 'Technical'),
            question.get('topic', ''),
        ),
    )
