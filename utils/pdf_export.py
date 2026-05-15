from __future__ import annotations

from io import BytesIO
from textwrap import wrap

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


SECTION_GAP = 18
LINE_HEIGHT = 14
LEFT_MARGIN = 40
TOP_START = 800


class PDFBuilder:
    def __init__(self, title: str) -> None:
        self.buffer = BytesIO()
        self.canvas = canvas.Canvas(self.buffer, pagesize=A4)
        self.width, self.height = A4
        self.y = TOP_START
        self.title = title
        self._header(title)

    def _header(self, title: str) -> None:
        self.canvas.setFont('Helvetica-Bold', 18)
        self.canvas.drawString(LEFT_MARGIN, self.y, title)
        self.y -= SECTION_GAP

    def add_heading(self, text: str) -> None:
        self._ensure_space(40)
        self.canvas.setFont('Helvetica-Bold', 13)
        self.canvas.drawString(LEFT_MARGIN, self.y, text)
        self.y -= LINE_HEIGHT + 4

    def add_paragraph(self, text: str, font_size: int = 10) -> None:
        self.canvas.setFont('Helvetica', font_size)
        for paragraph in text.split('\n'):
            lines = wrap(paragraph, 95) or ['']
            for line in lines:
                self._ensure_space(LINE_HEIGHT)
                self.canvas.drawString(LEFT_MARGIN, self.y, line)
                self.y -= LINE_HEIGHT
            self.y -= 4

    def add_bullets(self, items: list[str]) -> None:
        for item in items:
            self.add_paragraph(f'• {item}')

    def _ensure_space(self, required_height: int) -> None:
        if self.y - required_height < 50:
            self.canvas.showPage()
            self.y = TOP_START
            self.canvas.setFont('Helvetica', 10)

    def build(self) -> bytes:
        self.canvas.save()
        self.buffer.seek(0)
        return self.buffer.getvalue()


def build_performance_report(profile: dict, summary: dict, latest_attempts: list[dict]) -> bytes:
    pdf = PDFBuilder('AI Interview Preparation Report')
    pdf.add_heading('Candidate Profile')
    pdf.add_paragraph(
        f"Name: {profile.get('name', '-') }\n"
        f"Email: {profile.get('email', '-') }\n"
        f"Target Role: {profile.get('target_role', '-') }\n"
        f"Experience Level: {profile.get('experience_level', '-') }"
    )

    pdf.add_heading('Performance Summary')
    pdf.add_paragraph(
        f"Total Sessions: {summary.get('total_sessions', 0)}\n"
        f"Total Questions Answered: {summary.get('total_attempts', 0)}\n"
        f"Average Score: {summary.get('average_score', 0):.2f}/10\n"
        f"Best Topic: {summary.get('best_topic', 'N/A')}\n"
        f"Focus Area: {summary.get('weakest_topic', 'N/A')}"
    )

    pdf.add_heading('Strong Topics')
    pdf.add_bullets(summary.get('strong_topics', ['Not enough data yet.']))

    pdf.add_heading('Improvement Areas')
    pdf.add_bullets(summary.get('weak_topics', ['Not enough data yet.']))

    pdf.add_heading('Recent Attempts')
    if not latest_attempts:
        pdf.add_paragraph('No attempts recorded yet.')
    else:
        for attempt in latest_attempts[:8]:
            pdf.add_paragraph(
                f"Question: {attempt.get('question_text', '')}\n"
                f"Score: {attempt.get('score', 0)}/10\n"
                f"Topic: {attempt.get('topic', 'N/A')}\n"
                f"Technical Accuracy: {attempt.get('technical_accuracy', '')}\n"
                f"Communication: {attempt.get('communication_clarity', '')}"
            )
            pdf.add_paragraph('-' * 70)

    return pdf.build()
