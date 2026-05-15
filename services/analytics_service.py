from __future__ import annotations

import json
from collections import defaultdict
from statistics import mean
from typing import Any

import pandas as pd

from database import get_user_attempts, get_user_sessions


class AnalyticsService:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.sessions = get_user_sessions(user_id)
        self.attempts = get_user_attempts(user_id)

    def summary(self) -> dict[str, Any]:
        attempts = [dict(row) for row in self.attempts]
        sessions = [dict(row) for row in self.sessions]
        scores = [float(item['score']) for item in attempts] if attempts else []
        topic_scores: dict[str, list[float]] = defaultdict(list)
        for item in attempts:
            topic_scores[item.get('topic') or 'General'].append(float(item.get('score', 0)))

        avg_topic_scores = {topic: round(mean(vals), 2) for topic, vals in topic_scores.items() if vals}
        strongest = sorted(avg_topic_scores.items(), key=lambda kv: kv[1], reverse=True)
        weakest = sorted(avg_topic_scores.items(), key=lambda kv: kv[1])

        return {
            'total_sessions': len(sessions),
            'total_attempts': len(attempts),
            'average_score': round(mean(scores), 2) if scores else 0.0,
            'best_topic': strongest[0][0] if strongest else 'N/A',
            'weakest_topic': weakest[0][0] if weakest else 'N/A',
            'strong_topics': [f'{topic} ({score}/10)' for topic, score in strongest[:3]] or ['Not enough data yet.'],
            'weak_topics': [f'{topic} ({score}/10)' for topic, score in weakest[:3]] or ['Not enough data yet.'],
        }

    def attempts_df(self) -> pd.DataFrame:
        rows = [dict(row) for row in self.attempts]
        if not rows:
            return pd.DataFrame(columns=['created_at', 'score', 'topic', 'domain', 'difficulty'])
        df = pd.DataFrame(rows)
        df['created_at'] = pd.to_datetime(df['created_at'])
        return df

    def latest_attempts(self, count: int = 10) -> list[dict[str, Any]]:
        return [dict(row) for row in self.attempts[:count]]

    def topic_breakdown(self) -> pd.DataFrame:
        df = self.attempts_df()
        if df.empty:
            return pd.DataFrame(columns=['topic', 'avg_score'])
        grouped = df.groupby('topic', as_index=False)['score'].mean().rename(columns={'score': 'avg_score'})
        return grouped.sort_values('avg_score', ascending=False)

    def trend_df(self) -> pd.DataFrame:
        df = self.attempts_df()
        if df.empty:
            return pd.DataFrame(columns=['attempt_number', 'score'])
        df = df.sort_values('created_at').reset_index(drop=True)
        df['attempt_number'] = df.index + 1
        return df[['attempt_number', 'score', 'topic', 'created_at']]
