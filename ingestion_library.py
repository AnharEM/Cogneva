import os
import re
import json
import time
import sys
from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, text
from sentence_transformers import SentenceTransformer
from agno.agent import Agent
from agno.models.google import Gemini

from database import engine
from models import MainTopic, SubContent

load_dotenv()

# ─────────────────────────────────────────────────────────
# 1. INITIALIZATION
# ─────────────────────────────────────────────────────────
def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    SQLModel.metadata.create_all(engine)
    print("✅ Database tables and pgvector extension initialized.")

api_key = os.getenv("GOOGLE_API_KEY")

# The exact Gemini Parser Agent from your prototype
ingestion_agent = Agent(
    model=Gemini(id="gemini-3.1-flash-lite", api_key=api_key),
    description="You are a Clinical Parser Agent specialized in summarizing psychological textbooks.",
    instructions=[
        "Read the provided entire document.",
        "Generate a 300-500 word comprehensive summary for EACH top-level chapter.",
        "Include specific medications, statistical prevalence, and neurobiological circuits where applicable.",
        "CRITICAL: Return your output ONLY as a raw, valid JSON dictionary where the keys are the chapter numbers (as strings) and values are the summaries.",
        "Example format: {\"1\": \"Summary of chapter 1...\", \"2\": \"Summary of chapter 2...\"}",
        "Do not include markdown blocks (```json) or any other text. Just the JSON."
    ]
)

print("Loading Nomic embedding model (this may take a moment)...")
embedder = SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True)

# ─────────────────────────────────────────────────────────
# 2. PARSING LOGIC (From your LLM Wiki)
# ─────────────────────────────────────────────────────────
def parse_chapters(content: str):
    chapters = []
    current_num, current_title, current_lines = None, None, []
    
    for line in content.split('\n'):
        match = re.match(r"^(?:#|##)\s+(?:Chapter\s*(\d+)[:\.]?|(\d+)\.)\s*(.*)", line.strip(), re.IGNORECASE)
        if match:
            if current_num:
                chapters.append({"num": current_num, "title": current_title, "content": '\n'.join(current_lines)})
            current_num = match.group(1) or match.group(2)
            current_title = match.group(3).strip()
            current_lines = [line]
        else:
            if current_num:
                current_lines.append(line)
                
    if current_num:
        chapters.append({"num": current_num, "title": current_title, "content": '\n'.join(current_lines)})
        
    return chapters

def parse_and_ingest_book(md_filepath: str, book_title: str):
    print(f"\n" + "="*50)
    print(f"📖 Starting Ingestion for Book: {book_title}")
    print("="*50)
    
    with open(md_filepath, "r", encoding="utf-8") as f:
        content = f.read()

    max_retries = 3
    all_summaries = {}
    
    # --- GEMINI ONE-TIME SUMMARIZATION LOOP ---
    for attempt in range(max_retries):
        print(f"🧠 Sending '{book_title}' to Gemini (Attempt {attempt + 1}/{max_retries})...")
        
        try:
            response = ingestion_agent.run(f"This book is titled '{book_title}'. Generate summaries for all chapters:\n\n{content}")
            
            if not response or not response.content:
                print("⚠️ Empty response from API. Retrying in 5 seconds...")
                time.sleep(5)
                continue
                
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if not json_match:
                print("⚠️ No JSON dictionary found in output. Retrying in 5 seconds...")
                time.sleep(5)
                continue
                
            raw_json = json_match.group(0)
            raw_json = raw_json.replace('\\', '\\\\') # Fix for LaTeX math
            all_summaries = json.loads(raw_json)
            
            if len(all_summaries) < 2:
                print(f"⚠️ Received incomplete JSON: {all_summaries}. Retrying...")
                time.sleep(5)
                continue
                
            print(f"✅ Successfully received {len(all_summaries)} summaries from Gemini!")
            break 
            
        except json.JSONDecodeError:
            print("⚠️ JSON Decode Error. The LLM output was malformed. Retrying...")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ API Call Failed ({e}). Retrying...")
            time.sleep(5)
    else:
        print(f"❌ CRITICAL ERROR: Failed to parse {book_title} after {max_retries} attempts. Skipping.")
        return

    # --- NOMIC VECTORIZATION & LOCAL INSERTION ---
    chapters = parse_chapters(content)
    
    with Session(engine) as session:
        for ch in chapters:
            topic_number = ch["num"]
            topic_title = ch["title"]
            chapter_content = ch["content"]
            
            if topic_number not in all_summaries:
                print(f"⚠️  WARNING: Chapter {topic_number} ({topic_title}) missing from LLM summary! Skipping.")
                continue
                
            print(f"  -> Processing: Chapter {topic_number}: {topic_title}...")
            summary_text = all_summaries[topic_number]
            
            # Local Nomic Embedding (0 API cost)
            vector_input = f"search_document: {book_title} - {summary_text}"
            embedding = embedder.encode(vector_input).tolist()
            
            main_topic = MainTopic(
                book_title=book_title,
                topic_number=topic_number,
                title=topic_title,
                comprehensive_summary=summary_text,
                summary_embedding=embedding
            )
            session.add(main_topic)
            session.commit()
            session.refresh(main_topic)
            
            # Chunking and storing pristine raw content
            sub_sections = chapter_content.split('\n### ')
            for sub in sub_sections[1:]:
                sub_lines = sub.split('\n')
                sub_header = sub_lines[0].strip()
                sub_value = '\n'.join(sub_lines[1:]).strip()
                
                sub_match = re.match(r"([\d\.]+)\s*(.*)", sub_header)
                if sub_match:
                    sub_id, sub_title = sub_match.groups()
                else:
                    sub_id = "Unknown"
                    sub_title = sub_header

                sub_content = SubContent(
                    topic_id=main_topic.id,
                    sub_id=sub_id,
                    sub_title=sub_title,
                    content_value=sub_value
                )
                session.add(sub_content)
            
            session.commit()
            print(f"     ✅ Stored Chapter {topic_number} and its sub-contents.")

def process_all_books(books_dir: str = "books"):
    if not os.path.exists(books_dir):
        os.makedirs(books_dir)
        print(f"Created '{books_dir}'. Please place your .md files inside and run again.")
        sys.exit(0)

    md_files = [f for f in os.listdir(books_dir) if f.endswith(".md")]
    if not md_files:
        print(f"No .md files found in '{books_dir}'.")
        sys.exit(0)

    print(f"Found {len(md_files)} books to process.")
    for filename in md_files:
        filepath = os.path.join(books_dir, filename)
        book_title = filename.replace(".md", "").strip()
        parse_and_ingest_book(filepath, book_title)

if __name__ == "__main__":
    init_db()
    process_all_books("books")
    print("\n🎉 ALL BOOKS INGESTED SUCCESSFULLY!")