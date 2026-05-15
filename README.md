# AI Interview Preparation Bot

A full-stack AI interview preparation web application built with **Python + Streamlit + SQLite**.
It supports authentication, AI-powered question generation, timed mock interviews, answer evaluation, resume-based interviews, favorites, daily challenges, dashboards, and PDF performance reports.

## Features

- User login and signup
- Profile storage: name, email, target role, experience level
- AI-generated technical and HR interview questions
- Difficulty levels: Easy, Medium, Hard
- Mock interview flow with one question at a time
- Text answer mode and voice answer recording
- AI answer evaluation with score, feedback, missing points, and improved answer
- Resume PDF upload and resume-based personalized questions
- Performance dashboard with charts and topic analysis
- Daily challenge question
- Favorite questions
- Downloadable PDF performance report
- Demo mode that works even without API keys

## Tech Stack

- **Frontend/UI:** Streamlit, custom CSS
- **Backend:** Python
- **Database:** SQLite
- **AI Providers:** OpenAI or Gemini
- **Resume Parsing:** pdfplumber / pypdf
- **Charts:** Plotly
- **PDF Report:** ReportLab

## Project Structure

```bash
ai_interview_prep_bot/
│
├── app.py
├── config.py
├── database.py
├── requirements.txt
├── README.md
├── .env.example
├── interview_bot.db              # created automatically on first run
│
├── assets/
│   └── style.css
│
├── services/
│   ├── __init__.py
│   ├── ai_provider.py
│   ├── analytics_service.py
│   └── interview_service.py
│
├── utils/
│   ├── __init__.py
│   ├── auth.py
│   ├── pdf_export.py
│   ├── resume_parser.py
│   └── ui.py
│
└── .streamlit/
    └── config.toml
```

## Setup Instructions

### 1. Clone or unzip the project

```bash
cd ai_interview_prep_bot
```

### 2. Create virtual environment

**Windows**
```bash
py -3.10 -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Copy `.env.example` to `.env` and add your keys.

```bash
copy .env.example .env
```

or

```bash
cp .env.example .env
```

### 5. Run the app

```bash
streamlit run app.py
```

## Environment Variables

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

DEFAULT_PROVIDER=demo
DB_PATH=interview_bot.db
```

## How It Works

### Authentication
- Users can sign up and log in.
- Passwords are securely hashed with PBKDF2.
- User profile data is stored in SQLite.

### Question Generator
- Select domain, difficulty, and question type.
- The app sends a structured prompt to the configured AI provider.
- Questions are returned in JSON and displayed in the UI.
- In demo mode, built-in fallback questions are used.

### Mock Interview
- Generates a timed set of questions.
- Shows one question at a time.
- User answers by typing or recording audio.
- Audio can be transcribed when OpenAI speech-to-text is available.
- Each answer is evaluated immediately.

### AI Answer Evaluation
The evaluation returns:
- Score out of 10
- Technical accuracy feedback
- Communication clarity feedback
- Confidence level
- Missing points
- Improved version of the answer

### Resume Interview
- Upload a PDF resume.
- Text is extracted using `pdfplumber` or `pypdf`.
- Resume keywords and context are used to generate personalized questions.

### Performance Dashboard
- Stores attempts and sessions in SQLite.
- Visualizes score trends and topic-level averages.
- Identifies strong and weak topics.

### PDF Report
- Builds a downloadable performance report using ReportLab.
- Includes profile info, summary metrics, strong/weak areas, and recent attempts.

## Deployment Notes

### Streamlit Community Cloud
1. Push the project to GitHub.
2. Create a new Streamlit app.
3. Set `app.py` as the entry point.
4. Add environment variables in the Streamlit secrets or deployment settings.

### Render / Railway / VPS
- Install dependencies
- Set environment variables
- Run:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

## Important Notes

- Without API keys, the app runs in **demo mode**.
- Voice transcription currently uses OpenAI transcription when configured.
- SQLite is used by default for simplicity. You can migrate to MySQL later by replacing the database layer.

## Future Improvements

- MySQL or PostgreSQL support
- Admin analytics panel
- Interview question categories by company
- More advanced speech-to-text support for Gemini
- Video interview simulation
- Email reminders and daily streaks

## License

This project is provided for learning, portfolio use, and further customization.
