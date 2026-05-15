from __future__ import annotations

import io
import math
import time
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config import (
    APP_NAME,
    AVAILABLE_PROVIDERS,
    DEFAULT_PROVIDER,
    DIFFICULTY_LEVELS,
    EXPERIENCE_LEVELS,
    QUESTION_FOCUS,
    SUPPORTED_DOMAINS,
)
from database import (
    create_session,
    create_user,
    get_favorite_questions,
    get_latest_resume,
    get_resume_by_id,
    get_user_by_email,
    get_user_by_id,
    init_db,
    save_attempt,
    save_favorite_question,
    save_resume,
    update_user_profile,
    complete_session,
    delete_favorite_question,
)
from services.analytics_service import AnalyticsService
from services.interview_service import InterviewService
from utils.auth import hash_password, validate_email, validate_password, verify_password
from utils.pdf_export import build_performance_report
from utils.resume_parser import ResumeParserError, extract_text_from_pdf
from utils.ui import load_css, render_info_card, render_metric_card


st.set_page_config(page_title=APP_NAME, layout='wide', page_icon='🎯')
load_css()
init_db()


def init_session_state() -> None:
    defaults = {
        'authenticated': False,
        'user_id': None,
        'provider': DEFAULT_PROVIDER,
        'generated_questions': [],
        'resume_questions': [],
        'mock_session': None,
        'last_evaluation': None,
        'resume_id': None,
        'resume_text': '',
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_session_state()


def get_current_user() -> dict[str, Any] | None:
    if not st.session_state.get('user_id'):
        return None
    row = get_user_by_id(int(st.session_state['user_id']))
    return dict(row) if row else None


CURRENT_USER = get_current_user()


def auth_page() -> None:
    st.title('🎯 AI Interview Preparation Bot')
    st.caption('Practice smarter with AI-generated questions, mock interviews, resume-based coaching, and progress analytics.')

    col1, col2 = st.columns([1.1, 1])
    with col1:
        render_info_card(
            'What this app does',
            'Generate role-specific interview questions, run timed mock interviews, evaluate answers with AI, parse resumes, and track progress with a dashboard.'
        )
        render_info_card(
            'Demo mode included',
            'The project works without API keys using a built-in demo provider. Add OpenAI or Gemini keys in .env to enable live AI generation and evaluation.'
        )

    with col2:
        login_tab, signup_tab = st.tabs(['Login', 'Sign Up'])

        with login_tab:
            with st.form('login_form'):
                email = st.text_input('Email')
                password = st.text_input('Password', type='password')
                submitted = st.form_submit_button('Login', use_container_width=True)
                if submitted:
                    user = get_user_by_email(email)
                    if not user or not verify_password(password, user['password_hash']):
                        st.error('Invalid email or password.')
                    else:
                        st.session_state['authenticated'] = True
                        st.session_state['user_id'] = user['id']
                        st.success('Login successful.')
                        st.rerun()

        with signup_tab:
            with st.form('signup_form'):
                name = st.text_input('Full Name')
                email = st.text_input('Email Address')
                password = st.text_input('Create Password', type='password')
                target_role = st.selectbox('Target Job Role', SUPPORTED_DOMAINS)
                experience_level = st.selectbox('Experience Level', EXPERIENCE_LEVELS)
                submitted = st.form_submit_button('Create Account', use_container_width=True)
                if submitted:
                    if not name.strip():
                        st.error('Name is required.')
                    elif not validate_email(email):
                        st.error('Please enter a valid email address.')
                    else:
                        valid_pw, message = validate_password(password)
                        if not valid_pw:
                            st.error(message)
                        elif get_user_by_email(email):
                            st.error('An account with this email already exists.')
                        else:
                            create_user(name.strip(), email.strip(), hash_password(password), target_role, experience_level)
                            st.success('Account created successfully. Please log in.')


if not st.session_state['authenticated'] or CURRENT_USER is None:
    auth_page()
    st.stop()


INTERVIEW_SERVICE = InterviewService(st.session_state.get('provider', DEFAULT_PROVIDER))
ANALYTICS = AnalyticsService(CURRENT_USER['id'])
SUMMARY = ANALYTICS.summary()


def sidebar() -> str:
    with st.sidebar:
        st.markdown(f'### Welcome, {CURRENT_USER["name"]}')
        st.caption(f"Target role: {CURRENT_USER.get('target_role') or 'Not set'}")
        st.selectbox(
            'AI Provider',
            AVAILABLE_PROVIDERS,
            index=AVAILABLE_PROVIDERS.index(st.session_state.get('provider', DEFAULT_PROVIDER)),
            key='provider',
            help='Demo mode works offline. Add API keys in .env to enable OpenAI or Gemini.',
        )
        st.divider()
        page = st.radio(
            'Navigation',
            [
                'Dashboard',
                'Question Generator',
                'Mock Interview',
                'Resume Interview',
                'Daily Challenge',
                'Favorites',
                'Reports',
                'Profile',
            ],
        )
        st.divider()
        if st.button('Logout', use_container_width=True):
            for key in ['authenticated', 'user_id', 'generated_questions', 'resume_questions', 'mock_session', 'last_evaluation']:
                st.session_state[key] = False if key == 'authenticated' else None if key == 'user_id' else [] if 'questions' in key else None
            st.rerun()
    return page


PAGE = sidebar()


def render_dashboard() -> None:
    st.title('Performance Dashboard')
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card('Total Sessions', str(SUMMARY['total_sessions']), 'Completed and active interviews')
    with col2:
        render_metric_card('Questions Answered', str(SUMMARY['total_attempts']), 'All evaluated responses')
    with col3:
        render_metric_card('Average Score', f"{SUMMARY['average_score']:.2f}/10", 'Across all attempts')
    with col4:
        render_metric_card('Best Topic', SUMMARY['best_topic'], 'Strongest current area')

    trend_df = ANALYTICS.trend_df()
    topic_df = ANALYTICS.topic_breakdown()

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader('Score Progress')
        if trend_df.empty:
            st.info('No interview attempts yet. Complete one mock interview to unlock charts.')
        else:
            fig = px.line(trend_df, x='attempt_number', y='score', markers=True, hover_data=['topic', 'created_at'])
            fig.update_layout(height=360, xaxis_title='Attempt Number', yaxis_title='Score')
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader('Topic Analysis')
        if topic_df.empty:
            st.info('Topic analysis will appear after a few answers.')
        else:
            fig = px.bar(topic_df, x='topic', y='avg_score')
            fig.update_layout(height=360, xaxis_title='Topic', yaxis_title='Average Score')
            st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        render_info_card('Strong Topics', '<br>'.join(SUMMARY['strong_topics']))
    with c2:
        render_info_card('Focus Areas', '<br>'.join(SUMMARY['weak_topics']))

    st.subheader('Recent Interview Attempts')
    latest = ANALYTICS.latest_attempts(10)
    if not latest:
        st.info('No attempts recorded yet.')
    else:
        df = pd.DataFrame(latest)[['created_at', 'question_text', 'topic', 'score', 'difficulty']]
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_question_generator() -> None:
    st.title('Interview Question Generator')
    controls = st.columns(5)
    domain = controls[0].selectbox('Domain', SUPPORTED_DOMAINS, index=SUPPORTED_DOMAINS.index(CURRENT_USER['target_role']) if CURRENT_USER.get('target_role') in SUPPORTED_DOMAINS else 0)
    difficulty = controls[1].selectbox('Difficulty', DIFFICULTY_LEVELS)
    focus = controls[2].selectbox('Question Type', QUESTION_FOCUS)
    count = controls[3].slider('Number of Questions', 1, 10, 5)
    experience = controls[4].selectbox('Experience Level', EXPERIENCE_LEVELS, index=EXPERIENCE_LEVELS.index(CURRENT_USER['experience_level']) if CURRENT_USER.get('experience_level') in EXPERIENCE_LEVELS else 0)

    if st.button('Generate Questions', type='primary'):
        service = InterviewService(st.session_state['provider'])
        st.session_state['generated_questions'] = service.generate_questions(domain, difficulty, count, focus, experience)
        st.success('Questions generated successfully.')

    questions = st.session_state.get('generated_questions', [])
    if questions:
        st.subheader('Generated Questions')
        for idx, question in enumerate(questions, start=1):
            st.markdown(f"### Q{idx}. {question['question']}")
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            meta_col1.caption(f"Type: {question['type']}")
            meta_col2.caption(f"Topic: {question['topic']}")
            meta_col3.caption(f"Difficulty: {question['difficulty']}")
            if st.button(f"⭐ Save Question {idx}", key=f"save_gen_{idx}"):
                save_favorite_question(CURRENT_USER['id'], question)
                st.success('Saved to favorites.')
            st.divider()


def start_mock_session(questions: list[dict[str, Any]], session_type: str, domain: str, difficulty: str, focus: str, source_resume_id: int | None = None, time_limit: int = 120) -> None:
    session_id = create_session(CURRENT_USER['id'], session_type, domain, difficulty, focus, len(questions), source_resume_id)
    st.session_state['mock_session'] = {
        'session_id': session_id,
        'questions': questions,
        'current_index': 0,
        'answers': [],
        'domain': domain,
        'difficulty': difficulty,
        'focus': focus,
        'start_time': time.time(),
        'time_limit': time_limit,
        'source_resume_id': source_resume_id,
    }
    st.session_state['last_evaluation'] = None



def finish_mock_session() -> None:
    session = st.session_state.get('mock_session')
    if not session:
        return
    answers = session.get('answers', [])
    avg_score = sum(float(item['evaluation']['score']) for item in answers) / len(answers) if answers else 0.0
    complete_session(session['session_id'], avg_score)
    st.success(f"Mock interview completed. Average score: {avg_score:.2f}/10")
    st.session_state['mock_session'] = None



def render_mock_interview() -> None:
    st.title('Mock Interview Mode')

    session = st.session_state.get('mock_session')
    if not session:
        controls = st.columns(5)
        domain = controls[0].selectbox('Interview Domain', SUPPORTED_DOMAINS, key='mock_domain', index=SUPPORTED_DOMAINS.index(CURRENT_USER['target_role']) if CURRENT_USER.get('target_role') in SUPPORTED_DOMAINS else 0)
        difficulty = controls[1].selectbox('Difficulty', DIFFICULTY_LEVELS, key='mock_difficulty')
        focus = controls[2].selectbox('Question Type', QUESTION_FOCUS, key='mock_focus')
        total_questions = controls[3].slider('Questions', 1, 8, 5, key='mock_total_questions')
        time_limit = controls[4].slider('Seconds per Answer', 30, 300, 120, step=15, key='mock_timer')

        if st.button('Start Mock Interview', type='primary'):
            questions = InterviewService(st.session_state['provider']).generate_questions(
                domain=domain,
                difficulty=difficulty,
                count=total_questions,
                focus=focus,
                experience_level=CURRENT_USER.get('experience_level', ''),
            )
            start_mock_session(questions, 'mock', domain, difficulty, focus, None, time_limit)
            st.rerun()
        return

    questions = session['questions']
    idx = session['current_index']
    question = questions[idx]
    elapsed = int(time.time() - session['start_time'])
    remaining = max(0, session['time_limit'] - elapsed)
    st_autorefresh(interval=1000, key=f"timer_{session['session_id']}_{idx}")

    st.markdown(f"### Question {idx + 1} of {len(questions)}")
    st.progress((idx + 1) / len(questions))
    timer_col, domain_col, diff_col = st.columns(3)
    timer_col.metric('Time Remaining', f'{remaining}s')
    domain_col.metric('Domain', session['domain'])
    diff_col.metric('Difficulty', session['difficulty'])

    st.markdown(f"## {question['question']}")
    st.caption(f"Type: {question['type']} • Topic: {question['topic']}")

    text_answer = st.text_area('Type your answer', height=220, key=f'answer_text_{idx}')
    st.markdown('**Or record a voice answer**')
    audio_value = st.audio_input('Record your answer', key=f'audio_{idx}')
    transcribed_answer = ''

    if audio_value is not None:
        st.audio(audio_value)
        if st.button('Transcribe Voice Answer', key=f'transcribe_{idx}'):
            try:
                service = InterviewService(st.session_state['provider'])
                transcribed_answer = service.transcribe_audio(audio_value.getvalue(), f'answer_{idx}.wav')
                st.session_state[f'transcribed_{idx}'] = transcribed_answer
                st.success('Voice answer transcribed successfully.')
            except Exception as exc:
                st.warning(f'Voice transcription is unavailable: {exc}')

    transcribed_answer = st.session_state.get(f'transcribed_{idx}', '')
    if transcribed_answer:
        st.text_area('Transcribed Answer', transcribed_answer, height=160, key=f'transcribed_box_{idx}')

    answer_to_evaluate = text_answer.strip() or transcribed_answer.strip()

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button('Submit Answer', type='primary', use_container_width=True):
            if not answer_to_evaluate:
                st.error('Please type an answer or transcribe a voice answer before submitting.')
            else:
                evaluation = InterviewService(st.session_state['provider']).evaluate_answer(
                    question['question'],
                    answer_to_evaluate,
                    session['domain'],
                    session['difficulty'],
                    CURRENT_USER.get('experience_level', ''),
                )
                save_attempt(
                    session['session_id'],
                    CURRENT_USER['id'],
                    question,
                    text_answer,
                    transcribed_answer,
                    evaluation,
                )
                session['answers'].append({'question': question, 'answer': answer_to_evaluate, 'evaluation': evaluation})
                st.session_state['last_evaluation'] = evaluation
                st.session_state[f'answer_text_{idx}'] = ''
                st.session_state[f'transcribed_{idx}'] = ''
                if idx + 1 >= len(questions):
                    finish_mock_session()
                    st.rerun()
                else:
                    session['current_index'] += 1
                    session['start_time'] = time.time()
                    st.rerun()
    with col2:
        if st.button('End Interview', use_container_width=True):
            finish_mock_session()
            st.rerun()

    if st.session_state.get('last_evaluation'):
        render_evaluation_card(st.session_state['last_evaluation'])



def render_evaluation_card(evaluation: dict[str, Any]) -> None:
    st.subheader('AI Evaluation')
    m1, m2 = st.columns(2)
    m1.metric('Score', f"{evaluation.get('score', 0)}/10")
    m2.metric('Confidence Level', evaluation.get('confidence_level', 'N/A'))
    render_info_card('Technical Accuracy', evaluation.get('technical_accuracy', ''))
    render_info_card('Communication Clarity', evaluation.get('communication_clarity', ''))
    missing_points = evaluation.get('missing_points', [])
    strengths = evaluation.get('strengths', [])
    c1, c2 = st.columns(2)
    with c1:
        render_info_card('Missing Points', '<br>'.join(missing_points) if missing_points else 'No major gaps detected.')
    with c2:
        render_info_card('Strengths', '<br>'.join(strengths) if strengths else 'No strengths returned.')
    st.markdown('**Suggested Improved Answer**')
    st.write(evaluation.get('improved_answer', ''))



def render_resume_interview() -> None:
    st.title('Resume-Based Interview')
    st.caption('Upload a resume PDF to generate personalized interview questions from your own projects, skills, and experience.')

    upload = st.file_uploader('Upload Resume (PDF)', type=['pdf'])
    if upload is not None:
        try:
            file_bytes = upload.read()
            extracted_text = extract_text_from_pdf(file_bytes)
            resume_id = save_resume(CURRENT_USER['id'], upload.name, extracted_text)
            st.session_state['resume_id'] = resume_id
            st.session_state['resume_text'] = extracted_text
            st.success('Resume parsed successfully.')
        except ResumeParserError as exc:
            st.error(str(exc))

    latest_resume = get_resume_by_id(st.session_state['resume_id']) if st.session_state.get('resume_id') else get_latest_resume(CURRENT_USER['id'])
    if latest_resume:
        st.subheader('Latest Resume Extract')
        st.text_area('Extracted Text Preview', latest_resume['extracted_text'][:2500], height=260)
        c1, c2, c3 = st.columns(3)
        difficulty = c1.selectbox('Difficulty', DIFFICULTY_LEVELS, key='resume_difficulty')
        count = c2.slider('Questions', 1, 8, 5, key='resume_count')
        focus = c3.selectbox('Question Type', QUESTION_FOCUS, key='resume_focus')

        if st.button('Generate Personalized Questions', type='primary'):
            service = InterviewService(st.session_state['provider'])
            st.session_state['resume_questions'] = service.generate_questions(
                domain=CURRENT_USER.get('target_role') or 'Software Engineer',
                difficulty=difficulty,
                count=count,
                focus=focus,
                experience_level=CURRENT_USER.get('experience_level', ''),
                resume_text=latest_resume['extracted_text'],
            )
            st.success('Resume-based questions generated.')

        questions = st.session_state.get('resume_questions', [])
        if questions:
            st.subheader('Personalized Questions')
            for idx, question in enumerate(questions, start=1):
                st.markdown(f"### Q{idx}. {question['question']}")
                st.caption(f"Topic: {question['topic']} • Type: {question['type']}")
                if st.button(f"⭐ Save Resume Question {idx}", key=f'resume_save_{idx}'):
                    save_favorite_question(CURRENT_USER['id'], question)
                    st.success('Saved to favorites.')
                st.divider()
            if st.button('Start Resume-Based Mock Interview'):
                start_mock_session(
                    questions,
                    'resume',
                    CURRENT_USER.get('target_role') or 'Software Engineer',
                    difficulty,
                    focus,
                    latest_resume['id'],
                    120,
                )
                st.success('Resume interview started. Open Mock Interview from the sidebar.')



def render_daily_challenge() -> None:
    st.title('Daily Interview Challenge')
    c1, c2 = st.columns(2)
    domain = c1.selectbox('Role', SUPPORTED_DOMAINS, index=SUPPORTED_DOMAINS.index(CURRENT_USER['target_role']) if CURRENT_USER.get('target_role') in SUPPORTED_DOMAINS else 0, key='daily_domain')
    difficulty = c2.selectbox('Difficulty', DIFFICULTY_LEVELS, key='daily_difficulty')
    challenge = InterviewService(st.session_state['provider']).get_daily_challenge(domain, difficulty)

    st.markdown(f"## {challenge['question']}")
    st.caption(f"Topic: {challenge['topic']} • Type: {challenge['type']}")
    answer = st.text_area('Your challenge answer', height=220, key='daily_answer')
    if st.button('Evaluate Daily Challenge', type='primary'):
        if not answer.strip():
            st.error('Please write your answer first.')
        else:
            session_id = create_session(CURRENT_USER['id'], 'daily_challenge', domain, difficulty, challenge['type'], 1)
            evaluation = InterviewService(st.session_state['provider']).evaluate_answer(
                challenge['question'],
                answer,
                domain,
                difficulty,
                CURRENT_USER.get('experience_level', ''),
            )
            save_attempt(session_id, CURRENT_USER['id'], challenge, answer, '', evaluation)
            complete_session(session_id, evaluation.get('score', 0))
            render_evaluation_card(evaluation)



def render_favorites() -> None:
    st.title('Favorite Questions')
    favorites = get_favorite_questions(CURRENT_USER['id'])
    if not favorites:
        st.info('No favorite questions saved yet.')
        return
    for row in favorites:
        st.markdown(f"### {row['question_text']}")
        st.caption(f"{row['domain']} • {row['difficulty']} • {row['question_type']} • {row['topic']}")
        if st.button('Remove', key=f"del_fav_{row['id']}"):
            delete_favorite_question(row['id'], CURRENT_USER['id'])
            st.success('Removed from favorites.')
            st.rerun()
        st.divider()



def render_reports() -> None:
    st.title('Performance Report')
    latest_attempts = ANALYTICS.latest_attempts(8)
    pdf_bytes = build_performance_report(CURRENT_USER, SUMMARY, latest_attempts)

    st.subheader('Quick Summary')
    render_info_card(
        'Report Overview',
        f"Sessions: {SUMMARY['total_sessions']}<br>Questions Answered: {SUMMARY['total_attempts']}<br>Average Score: {SUMMARY['average_score']:.2f}/10"
    )
    st.download_button(
        'Download Performance Report (PDF)',
        data=pdf_bytes,
        file_name='interview_performance_report.pdf',
        mime='application/pdf',
        use_container_width=True,
    )



def render_profile() -> None:
    st.title('Profile Settings')
    with st.form('profile_form'):
        name = st.text_input('Name', value=CURRENT_USER.get('name', ''))
        email = st.text_input('Email', value=CURRENT_USER.get('email', ''), disabled=True)
        target_role = st.selectbox('Target Role', SUPPORTED_DOMAINS, index=SUPPORTED_DOMAINS.index(CURRENT_USER['target_role']) if CURRENT_USER.get('target_role') in SUPPORTED_DOMAINS else 0)
        experience_level = st.selectbox('Experience Level', EXPERIENCE_LEVELS, index=EXPERIENCE_LEVELS.index(CURRENT_USER['experience_level']) if CURRENT_USER.get('experience_level') in EXPERIENCE_LEVELS else 0)
        submitted = st.form_submit_button('Update Profile', use_container_width=True)
        if submitted:
            update_user_profile(CURRENT_USER['id'], name, target_role, experience_level)
            st.success('Profile updated successfully.')
            st.rerun()


page_map = {
    'Dashboard': render_dashboard,
    'Question Generator': render_question_generator,
    'Mock Interview': render_mock_interview,
    'Resume Interview': render_resume_interview,
    'Daily Challenge': render_daily_challenge,
    'Favorites': render_favorites,
    'Reports': render_reports,
    'Profile': render_profile,
}

page_map[PAGE]()
