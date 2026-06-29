import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session

load_dotenv()

# Fetches the database URL from the Docker environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set in .env")

# Initialize the SQLModel engine
engine = create_engine(DATABASE_URL)

def get_session():
    """Dependency generator for FastAPI routes."""
    with Session(engine) as session:
        yield session