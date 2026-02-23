import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "lem.db"


def _resolve_db_path() -> Path:
    configured = os.getenv("LEM_DB_PATH")
    if not configured:
        return DEFAULT_DB_PATH

    path = Path(configured)
    if path.is_absolute():
        return path
    return BASE_DIR / path


DB_PATH = _resolve_db_path()


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id TEXT NOT NULL,
    competency TEXT NOT NULL,
    response_text TEXT NOT NULL,
    score REAL,
    level TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    llm_model TEXT,
    prompt_versions TEXT,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS dimension_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    score REAL,
    weight REAL,
    points REAL,
    justification TEXT,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    citation TEXT NOT NULL,
    is_present INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL UNIQUE,
    summary TEXT,
    recommendation TEXT,
    strengths TEXT,
    development_areas TEXT,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pipeline_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER,
    step_name TEXT NOT NULL,
    input_data TEXT,
    output_data TEXT,
    prompt_used TEXT,
    prompt_version TEXT,
    duration_ms INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_assessments_created_at ON assessments(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assessments_competency ON assessments(competency);
CREATE INDEX IF NOT EXISTS idx_assessments_participant ON assessments(participant_id);
CREATE INDEX IF NOT EXISTS idx_dimension_scores_assessment ON dimension_scores(assessment_id);
CREATE INDEX IF NOT EXISTS idx_evidence_assessment ON evidence(assessment_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_assessment ON pipeline_steps(assessment_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_step_name ON pipeline_steps(step_name);

CREATE TABLE IF NOT EXISTS sample_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    content TEXT NOT NULL,
    response_type TEXT NOT NULL DEFAULT 'GEN_AI' CHECK(response_type IN ('REAL', 'GEN_AI', 'GEN_HUMAN')),
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system'
);
"""


@asynccontextmanager
async def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH.as_posix())
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        await conn.close()


MIGRATIONS = [
    "ALTER TABLE assessments ADD COLUMN total_tokens INTEGER DEFAULT 0",
    "ALTER TABLE assessments ADD COLUMN total_cost_usd REAL DEFAULT 0.0",
]


async def init_db() -> None:
    async with get_connection() as conn:
        await conn.executescript(CREATE_TABLES_SQL)
        for migration in MIGRATIONS:
            try:
                await conn.execute(migration)
            except Exception:
                pass
        await conn.commit()
