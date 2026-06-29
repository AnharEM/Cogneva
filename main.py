from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Security
from fastapi.security import APIKeyHeader
from sqlmodel import Session, select, SQLModel
from sqlalchemy import text
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List
import json
import os

from database import get_session, engine
from models import User, ChatTurn, HydratedState, ChatSessionRecord
from agent import get_psychologist_agent, embedder
from agno.agent import Agent
from agno.models.google import Gemini

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the pgvector extension is enabled before creating tables
    with Session(engine) as session:
        session.exec(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        session.commit()
        
    # Ensure database tables exist at startup
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(title="AI Psychologist API", version="1.2.0", lifespan=lifespan)

# --- Pydantic Schemas ---
class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    user_input: str

class ChatResponse(BaseModel):
    response: str
    therapeutic_phase: int
    turn_count: int
    emotional_state: str 
    intensity: float
    response_mode: str

# --- BEGIN NEW ADDITIONS: FRONTEND INTEGRATION (Can be safely reverted) ---
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.getenv("INTERNAL_API_KEY")
    if expected_key and api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key
# --- END NEW ADDITIONS ---

# --- Endpoints ---
@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    request: ChatRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    # --- BEGIN NEW ADDITIONS: FRONTEND INTEGRATION (Can be safely reverted) ---
    api_key: str = Depends(verify_api_key)
    # --- END NEW ADDITIONS ---
):
    # 1. Fetch User (Auto-register if it's their first time ever)
    user = db.get(User, request.user_id)
    if not user:
        user = User(id=request.user_id, therapeutic_phase=1)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 1.5 Ensure Session Exists
    session_id = request.session_id or request.user_id
    chat_session = db.get(ChatSessionRecord, session_id)
    if not chat_session:
        chat_session = ChatSessionRecord(id=session_id, user_id=user.id, title="Therapy Session")
        db.add(chat_session)
        db.commit()

    # 2. Save User Turn
    db.add(ChatTurn(user_id=user.id, session_id=session_id, role="user", content=request.user_input, turn_number=0))
    db.commit()

    # 3. Fetch latest Hydrated State
    latest_state = db.exec(
        select(HydratedState)
        .where(HydratedState.user_id == user.id)
        .order_by(HydratedState.id.desc())
    ).first()

    # 4. Inline Emotion Tracking (Synchronous)
    api_key = os.getenv("GOOGLE_API_KEY")
    emotion_agent = Agent(model=Gemini(id="gemini-3.1-flash-lite", api_key=api_key))
    
    emotion_prompt = f"""
    Analyze the user's latest message: "{request.user_input}"
    Determine the current emotional state, intensity, and recommended therapist response mode.
    - "emotional_state": 1-2 words (e.g., "Relieved", "Anxious", "Neutral")
    - "intensity": a float from 0.0 to 1.0 (e.g., 0.2 for low, 0.8 for high)
    - "response_mode": 1-2 words (e.g., "Validate", "Grounding", "Explore")
    Output ONLY valid JSON matching this schema:
    {{"emotional_state": "...", "intensity": 0.0, "response_mode": "..."}}
    """
    
    try:
        emo_result = emotion_agent.run(emotion_prompt)
        raw_emo_json = emo_result.content.replace('```json', '').replace('```', '').strip()
        emo_data = json.loads(raw_emo_json)
        current_emotion = emo_data.get("emotional_state", "Neutral")
        current_intensity = float(emo_data.get("intensity", 0.0))
        current_mode = emo_data.get("response_mode", "Explore")
    except Exception as e:
        print(f"Real-time emotion tracking failed: {e}")
        current_emotion = latest_state.emotional_state if latest_state else "Neutral"
        current_intensity = latest_state.intensity if latest_state else 0.0
        current_mode = latest_state.response_mode if latest_state else "Establish Rapport"

    # 5. Build Memory Context Layout
    if latest_state:
        state_context = (
            f"--- PATIENT HISTORY ---\n"
            f"SUMMARY & FACTS: {latest_state.state_summary}\n"
            f"CURRENT EMOTION: {current_emotion} | INTENSITY: {current_intensity}/1.0\n"
            f"REQUIRED THERAPIST POSTURE: {current_mode}\n"
        )
        dynamic_instruction = latest_state.dynamic_instruction
    else:
        state_context = (
            f"--- PATIENT HISTORY ---\n"
            f"SUMMARY & FACTS: None. This is a new patient.\n"
            f"CURRENT EMOTION: {current_emotion} | INTENSITY: {current_intensity}/1.0\n"
            f"REQUIRED THERAPIST POSTURE: {current_mode}\n"
        )
        dynamic_instruction = "PHASE 1: This is a new patient. Ask ONE curious, open question to get them talking. Do NOT give advice yet."

    # 6. Fetch Short-Term Working Memory
    recent_turns = db.exec(
        select(ChatTurn)
        .where(ChatTurn.session_id == session_id)
        .order_by(ChatTurn.created_at.desc())
        .limit(50)
    ).all()
    recent_turns.reverse()
    
    recent_transcript = "\n".join([f"{t.role.upper()}: {t.content}" for t in recent_turns[:-1]])

    # 7. Initialize dynamic Agent and format prompt clearly
    agent = get_psychologist_agent(user.therapeutic_phase, dynamic_instruction)

    full_prompt = f"""
{state_context}

--- RECENT CONVERSATION HISTORY ---
{recent_transcript}
-----------------------------------

USER CURRENTLY SAYS: {request.user_input}
    """
    
    ai_response = agent.run(full_prompt)

    # 8. Save AI Turn
    db.add(ChatTurn(user_id=user.id, session_id=session_id, role="ai", content=ai_response.content, turn_number=0))
    db.commit()

    # 9. Smart Hydration Triggers
    total_db_turns = db.exec(select(ChatTurn.id).where(ChatTurn.user_id == user.id)).all()
    turn_count = len(total_db_turns) // 2 

    word_count = len(request.user_input.split())
    is_first_turn = (turn_count == 1)
    is_context_dump = (word_count >= 15) # Trigger lowered so 18-word intros trigger Personalizer
    is_cycle_turn = (turn_count > 0 and turn_count % 20 == 0)

    if is_first_turn or is_context_dump or is_cycle_turn:
        background_tasks.add_task(hydrate_and_evaluate_phase, user.id)

    return ChatResponse(
        response=ai_response.content,
        therapeutic_phase=user.therapeutic_phase,
        turn_count=turn_count,
        emotional_state=current_emotion,
        intensity=current_intensity,
        response_mode=current_mode
    )

# --- BEGIN NEW ADDITIONS: FRONTEND INTEGRATION (Can be safely reverted) ---
class HistoryTurn(BaseModel):
    role: str
    content: str
    created_at: str

@app.get("/chat/history/{session_id}", response_model=List[HistoryTurn])
def get_chat_history(
    session_id: str,
    db: Session = Depends(get_session),
    api_key: str = Depends(verify_api_key)
):
    """Fetches the chat history for a specific session to restore it."""
    chat_session = db.get(ChatSessionRecord, session_id)
    if not chat_session:
        return []
    
    turns = db.exec(
        select(ChatTurn)
        .where(ChatTurn.session_id == session_id)
        .order_by(ChatTurn.created_at.asc())
    ).all()
    
    return [
        HistoryTurn(
            role=turn.role, 
            content=turn.content, 
            created_at=turn.created_at.isoformat()
        ) 
        for turn in turns
    ]

# --- NEW SESSION ROUTES ---
class SessionInfo(BaseModel):
    id: str
    title: str
    created_at: str

@app.get("/chat/sessions/{user_id}", response_model=List[SessionInfo])
def get_chat_sessions(
    user_id: str,
    db: Session = Depends(get_session),
    api_key: str = Depends(verify_api_key)
):
    sessions = db.exec(
        select(ChatSessionRecord)
        .where(ChatSessionRecord.user_id == user_id)
        .order_by(ChatSessionRecord.created_at.desc())
    ).all()
    return [SessionInfo(id=s.id, title=s.title, created_at=s.created_at.isoformat()) for s in sessions]

class RenameSessionRequest(BaseModel):
    title: str

@app.put("/chat/sessions/{session_id}")
def rename_chat_session(
    session_id: str,
    request: RenameSessionRequest,
    db: Session = Depends(get_session),
    api_key: str = Depends(verify_api_key)
):
    session_record = db.get(ChatSessionRecord, session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found")
    session_record.title = request.title
    db.add(session_record)
    db.commit()
    return {"status": "ok"}

@app.delete("/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_session),
    api_key: str = Depends(verify_api_key)
):
    session_record = db.get(ChatSessionRecord, session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session_record)
    db.commit()
    return {"status": "ok"}

@app.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_session),
    api_key: str = Depends(verify_api_key)
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"status": "ok"}
# --- END NEW ADDITIONS ---


# --- Background Hydration Task ---
def hydrate_and_evaluate_phase(user_id: str):
    """Runs in the background dynamically to create Cumulative memory."""
    with Session(engine) as db:
        user = db.get(User, user_id)
        if not user:
            return

        recent_turns = db.exec(
            select(ChatTurn)
            .where(ChatTurn.user_id == user_id)
            .order_by(ChatTurn.created_at.desc())
            .limit(40)
        ).all()
        recent_turns.reverse() 

        transcript = "\n".join([f"{t.role}: {t.content}" for t in recent_turns])

        latest_state = db.exec(
            select(HydratedState)
            .where(HydratedState.user_id == user_id)
            .order_by(HydratedState.id.desc())
        ).first()
        previous_summary = latest_state.state_summary if latest_state else "None. First evaluation."

        api_key = os.getenv("GOOGLE_API_KEY")
        summarizer_agent = Agent(
            model=Gemini(id="gemini-3.1-flash-lite", api_key=api_key)
        )
        
        eval_prompt = f"""
        You are a Clinical Supervisor Agent. Analyze this patient-therapist transcript alongside their past history.
        
        1. ASSESS TRUST & PHASE: Look at how vulnerable the patient is being. 
           - FAST-TRACKING MANDATE: If the user provides a detailed context dump early, fast-track them immediately to Phase 2 or Phase 3.
        
        2. CUMULATIVE STATE SUMMARY: Update the patient's lifelong file. 
           - VITAL FACTS: Explicitly carry over all hard facts (Names, dates, jobs, etc) from the previous summary. Add new ones from the transcript.
           - CLINICAL SUMMARY: Summarize their current emotional state, triggers, and progress.
           - Format exactly like: "VITAL FACTS: [Name: X, Job: Y] | CLINICAL SUMMARY: [3 sentences...]"
           
        3. EMOTIONAL PROFILING:
           - "emotional_state": A 1-2 word label of their primary emotion.
           - "intensity": A float from 0.0 to 1.0.
           - "response_mode": The tactical stance the therapist must take: "Validate", "Explore", "Comfort", "Challenge", or "Grounding".
           
        4. WRITE THE DYNAMIC INSTRUCTION: Write a strict, 3-sentence system prompt dictating how the therapist must speak based on the Response Mode and Intensity.
        
        Respond ONLY with a valid JSON object matching this schema:
        {{
            "state_summary": "...", 
            "recommended_phase": <int 1-4>, 
            "dynamic_instruction": "...",
            "emotional_state": "...",
            "intensity": <float 0.0-1.0>,
            "response_mode": "..."
        }}
        
        --- PREVIOUS STATE SUMMARY ---
        {previous_summary}
        
        --- NEW TRANSCRIPT ---
        {transcript}
        """
        
        result = summarizer_agent.run(eval_prompt)
        
        try:
            raw_json = result.content.replace('```json', '').replace('```', '').strip()
            data = json.loads(raw_json)
            
            embedding = embedder.encode(f"patient_state: {data['state_summary']}").tolist()
            
            total_db_turns = db.exec(select(ChatTurn.id).where(ChatTurn.user_id == user_id)).all()
            current_turn_count = len(total_db_turns) // 2
            
            new_state = HydratedState(
                user_id=user_id,
                start_turn=max(0, current_turn_count - 20), 
                end_turn=current_turn_count,        
                state_summary=data["state_summary"],
                state_embedding=embedding,
                dynamic_instruction=data["dynamic_instruction"],
                emotional_state=data["emotional_state"],
                intensity=float(data["intensity"]),
                response_mode=data["response_mode"]
            )
            db.add(new_state)

            if data["recommended_phase"] > user.therapeutic_phase and data["recommended_phase"] <= 4:
                user.therapeutic_phase = data["recommended_phase"]
                db.add(user)

            db.commit()
            print(f"✅ Hydrated! Phase: {user.therapeutic_phase} | Mood: {data['emotional_state']} | Mode: {data['response_mode']}")
            
        except Exception as e:
            print(f"⚠️ Hydration failed for user {user_id}: {e}")