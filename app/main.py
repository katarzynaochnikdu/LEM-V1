"""
FastAPI aplikacja - System Oceny Kompetencji LEM
Obsługa 4 kompetencji menedżerskich z izolowanym cyklem per kompetencja
"""

import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv

from app.models import (
    AssessmentRequest,
    AssessmentResponse,
    HealthResponse,
    ParsedResponse,
    MappedResponse,
    ScoringResult,
    Feedback,
    WymiarEvidence,
    DimensionScore,
)
from app.modules.parser import ResponseParser
from app.modules.mapper import ResponseMapper
from app.modules.scorer import CompetencyScorer
from app.modules.feedback import FeedbackGenerator
from app.rubric import (
    get_available_competencies,
    get_competency_info,
    get_wymiary_for_competency,
    COMPETENCY_REGISTRY,
)
from app.auth import (
    ensure_admin_exists, verify_user, create_session,
    get_session, delete_session, add_user, list_users,
    SESSION_COOKIE,
)
from app.prompt_manager import (
    list_modules as pm_list_modules,
    list_versions as pm_list_versions,
    get_prompt as pm_get_prompt,
    save_prompt as pm_save_prompt,
    activate_version as pm_activate_version,
    get_active_versions as pm_get_active_versions,
)

load_dotenv()

app = FastAPI(
    title="System Oceny Kompetencji LEM",
    description="Automatyczna ocena kompetencji menedżerskich z wykorzystaniem AI",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_PATHS = {"/", "/health", "/login", "/api/auth/login", "/api/auth/logout"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/static/"):
        return await call_next(request)
    token = request.cookies.get(SESSION_COOKIE)
    if not token or not get_session(token):
        if path.startswith("/api/"):
            return JSONResponse(status_code=401, content={"detail": "Nie zalogowano"})
        return RedirectResponse(url="/login", status_code=302)
    request.state.user = get_session(token)
    return await call_next(request)


@app.on_event("startup")
async def startup():
    ensure_admin_exists()


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
async def api_login(req: LoginRequest, response: Response):
    role = verify_user(req.username, req.password)
    if not role:
        raise HTTPException(status_code=401, detail="Nieprawidłowy login lub hasło")
    token = create_session(req.username, role)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )
    return {"ok": True, "username": req.username, "role": role}


@app.post("/api/auth/logout")
async def api_logout(response: Response, lem_session: Optional[str] = Cookie(None)):
    if lem_session:
        delete_session(lem_session)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
async def api_me(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Nie zalogowano")
    return {"username": user["username"], "role": user["role"]}


class AddUserRequest(BaseModel):
    username: str
    password: str = Field(..., min_length=4)
    role: str = "user"


@app.post("/api/auth/users")
async def api_add_user(req: AddUserRequest, request: Request):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin może dodawać użytkowników")
    ok = add_user(req.username, req.password, req.role)
    if not ok:
        raise HTTPException(status_code=409, detail="Użytkownik już istnieje")
    return {"ok": True, "username": req.username}


@app.get("/api/auth/users")
async def api_list_users(request: Request):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin")
    return list_users()


# ---------------------------------------------------------------------------
# FACTORY - nowe instancje modułów per kompetencja (bez singletona)
# ---------------------------------------------------------------------------

def get_modules(competency: str = "delegowanie"):
    """Factory: nowe instancje modułów pipeline dla danej kompetencji."""
    if competency not in get_available_competencies():
        raise ValueError(f"Nieznana kompetencja: {competency}. Dostępne: {get_available_competencies()}")
    return (
        ResponseParser(competency),
        ResponseMapper(competency),
        CompetencyScorer(competency),
        FeedbackGenerator(competency),
    )


# ---------------------------------------------------------------------------
# HEALTH
# ---------------------------------------------------------------------------

@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(status="healthy", version="2.0.0")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", version="2.0.0")


# ---------------------------------------------------------------------------
# COMPETENCIES API
# ---------------------------------------------------------------------------

@app.get("/api/competencies")
async def list_competencies(request: Request):
    """Lista dostępnych kompetencji z wymiarami."""
    result = []
    for key, info in COMPETENCY_REGISTRY.items():
        result.append({
            "id": key,
            "nazwa": info["nazwa"],
            "wymiary_count": len(info["wymiary"]),
            "algorytm_steps": len(info["algorytm"]),
        })
    return result


@app.get("/api/competencies/{name}/dimensions")
async def get_competency_dimensions(name: str, request: Request, detail: bool = False):
    """Wymiary i algorytm danej kompetencji."""
    if name not in COMPETENCY_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Kompetencja '{name}' nie istnieje")
    info = get_competency_info(name)
    dimensions = {}
    for key, value in info["wymiary"].items():
        dim_data = {
            "nazwa": value["nazwa"],
            "opis": value["opis"],
            "poziomy_count": len(value["poziomy"]),
        }
        if detail:
            dim_data["poziomy"] = {
                str(k): {"opis": v["opis"], "zachowania": v.get("zachowania", [])}
                for k, v in value["poziomy"].items()
            }
        dimensions[key] = dim_data
    return {
        "competency": name,
        "nazwa": info["nazwa"],
        "algorytm": info["algorytm"],
        "dimensions": dimensions,
        "total_dimensions": len(dimensions),
    }


# ---------------------------------------------------------------------------
# ASSESS - pełny pipeline
# ---------------------------------------------------------------------------

@app.post("/assess", response_model=AssessmentResponse)
async def assess_competency(request: AssessmentRequest):
    """Pełny pipeline oceny kompetencji (izolowany cykl per kompetencja)."""
    try:
        competency = request.competency
        parser, mapper, scorer, feedback_gen = get_modules(competency)

        parsed_response = await parser.parse(request.response_text)

        is_valid, missing = parser.validate_parsed_response(parsed_response)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Odpowiedź niekompletna. Brakujące sekcje: {', '.join(missing)}"
            )

        mapped_response = await mapper.map(parsed_response)
        scoring_result = await scorer.score(mapped_response)
        feedback = await feedback_gen.generate(scoring_result)

        evidence_dict = {
            k: v.znalezione_fragmenty
            for k, v in mapped_response.evidence.items()
        }
        dimension_scores_dict = {
            k: v.ocena
            for k, v in scoring_result.dimension_scores.items()
        }

        return AssessmentResponse(
            participant_id=request.participant_id,
            competency=competency,
            score=scoring_result.ocena,
            level=scoring_result.poziom,
            evidence=evidence_dict,
            feedback=feedback,
            dimension_scores=dimension_scores_dict,
            scoring_details=scoring_result,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd przetwarzania: {str(e)}")


# ---------------------------------------------------------------------------
# DIAGNOSTIC ENDPOINTS - krok po kroku
# ---------------------------------------------------------------------------

class DiagnosticParseRequest(BaseModel):
    response_text: str = Field(..., min_length=50)
    competency: str = Field(default="delegowanie")


@app.post("/api/diagnostic/parse")
async def diagnostic_parse(request: DiagnosticParseRequest):
    """Krok 1: Strukturyzacja odpowiedzi na sekcje"""
    try:
        parser, _, _, _ = get_modules(request.competency)
        active_prompt = pm_get_prompt("parse", competency=request.competency)
        prompt_sent = parser.prompt_template.format(response_text=request.response_text)
        parsed = await parser.parse(request.response_text)
        return {
            "sections": parsed.sections,
            "raw_text": parsed.raw_text,
            "competency": request.competency,
            "_prompt": {
                "system": "Jesteś ekspertem w analizie strukturalnej tekstów. Zwracasz wyłącznie poprawny JSON.",
                "user": prompt_sent,
            },
            "_prompt_meta": {
                "module": "parse",
                "competency": request.competency,
                "active_version": active_prompt.get("version"),
                "active_template": active_prompt.get("content"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagnostic/map")
async def diagnostic_map(request: dict):
    """Krok 2: Ekstrakcja dowodów dla wymiarów"""
    try:
        competency = request.get("competency", "delegowanie")
        _, mapper, _, _ = get_modules(competency)
        active_prompt = pm_get_prompt("map", competency=competency)

        sections = request.get("sections", {})
        raw_text = request.get("raw_text", "")

        # Backward compat: stary format z hardkodowanymi polami
        if not sections:
            sections = {}
            for key in ["przygotowanie", "przebieg", "decyzje", "efekty"]:
                if key in request:
                    sections[key] = request[key]

        parsed = ParsedResponse(sections=sections, raw_text=raw_text)
        sections_text = "\n\n".join(
            f"{k.upper().replace('_', ' ')}:\n{v}" for k, v in parsed.sections.items() if v
        )
        prompt_sent = mapper.prompt_template.format(parsed_response=sections_text)
        mapped = await mapper.map(parsed)

        evidence_out = {}
        for key, ev in mapped.evidence.items():
            evidence_out[key] = {
                "wymiar": ev.wymiar,
                "znalezione_fragmenty": ev.znalezione_fragmenty,
                "czy_obecny": ev.czy_obecny,
                "notatki": ev.notatki,
            }
        return {
            "evidence": evidence_out,
            "parsed_response": {"sections": parsed.sections, "raw_text": parsed.raw_text},
            "competency": competency,
            "_prompt": {
                "system": "Jesteś ekspertem w ocenie kompetencji menedżerskich. Zwracasz wyłącznie poprawny JSON z ekstrakcją cytatów.",
                "user": prompt_sent,
            },
            "_prompt_meta": {
                "module": "map",
                "competency": competency,
                "active_version": active_prompt.get("version"),
                "active_template": active_prompt.get("content"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagnostic/score")
async def diagnostic_score(request: dict):
    """Krok 3: Scoring - ocena wymiarów i wynik końcowy"""
    try:
        competency = request.get("competency", "delegowanie")
        _, _, scorer, _ = get_modules(competency)
        active_prompt = pm_get_prompt("score", competency=competency)
        wymiary = get_wymiary_for_competency(competency)

        evidence_dict = {}
        for key, ev_data in request.get("evidence", {}).items():
            evidence_dict[key] = WymiarEvidence(
                wymiar=ev_data.get("wymiar", key),
                znalezione_fragmenty=ev_data.get("znalezione_fragmenty", []),
                czy_obecny=ev_data.get("czy_obecny", False),
                notatki=ev_data.get("notatki"),
            )

        pr_data = request.get("parsed_response", {})
        sections = pr_data.get("sections", {})
        raw_text = pr_data.get("raw_text", "")

        # Backward compat
        if not sections:
            sections = {}
            for key in ["przygotowanie", "przebieg", "decyzje", "efekty"]:
                if key in pr_data:
                    sections[key] = pr_data[key]

        parsed = ParsedResponse(sections=sections, raw_text=raw_text)
        mapped = MappedResponse(evidence=evidence_dict, parsed_response=parsed)

        score_prompts = {}
        for wymiar_key, ev in evidence_dict.items():
            if ev.czy_obecny and len(ev.znalezione_fragmenty) > 0 and wymiar_key in wymiary:
                wdef = wymiary[wymiar_key]
                score_prompts[wymiar_key] = (
                    f"Oceń jakość realizacji wymiaru kompetencji.\n\n"
                    f"WYMIAR: {wdef['nazwa']}\nOPIS: {wdef['opis']}\n\n"
                    f"POZIOMY JAKOŚCI:\n{scorer._format_levels(wdef['poziomy'])}\n\n"
                    f"ZNALEZIONE DOWODY W ODPOWIEDZI:\n{scorer._format_evidence(ev)}\n\n"
                    f"ZADANIE:\nOceń jakość realizacji tego wymiaru w skali 0.0 - 1.0\n"
                    f"Zwróć TYLKO liczbę (np. 0.75) bez dodatkowych komentarzy."
                )
            else:
                score_prompts[wymiar_key] = "(wymiar nieobecny – pominięty, ocena = 0.0)"

        scoring = await scorer.score(mapped)
        dim_out = {}
        for key, ds in scoring.dimension_scores.items():
            dim_out[key] = {
                "wymiar": ds.wymiar,
                "ocena": ds.ocena,
                "waga": ds.waga,
                "punkty": ds.punkty,
                "uzasadnienie": ds.uzasadnienie,
            }
        return {
            "ocena": scoring.ocena,
            "ocena_delegowanie": scoring.ocena,  # backward compat
            "poziom": scoring.poziom,
            "dimension_scores": dim_out,
            "competency": competency,
            "evidence": {k: {
                "wymiar": v.wymiar,
                "znalezione_fragmenty": v.znalezione_fragmenty,
                "czy_obecny": v.czy_obecny,
                "notatki": v.notatki,
            } for k, v in mapped.evidence.items()},
            "parsed_response": {"sections": parsed.sections, "raw_text": parsed.raw_text},
            "_prompt": {
                "system": "Jesteś ekspertem w ocenie kompetencji menedżerskich. Zwracasz tylko liczbę z zakresu 0.0-1.0.",
                "per_dimension": score_prompts,
            },
            "_prompt_meta": {
                "module": "score",
                "competency": competency,
                "active_version": active_prompt.get("version"),
                "active_template": active_prompt.get("content"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagnostic/feedback")
async def diagnostic_feedback(request: dict):
    """Krok 4: Generowanie feedbacku rozwojowego"""
    try:
        competency = request.get("competency", "delegowanie")
        _, _, _, fg = get_modules(competency)
        active_prompt = pm_get_prompt("feedback", competency=competency)

        pr_data = request.get("parsed_response", {})
        sections = pr_data.get("sections", {})
        raw_text = pr_data.get("raw_text", "")

        if not sections:
            sections = {}
            for key in ["przygotowanie", "przebieg", "decyzje", "efekty"]:
                if key in pr_data:
                    sections[key] = pr_data[key]

        parsed = ParsedResponse(sections=sections, raw_text=raw_text)

        evidence_dict = {}
        for key, ev_data in request.get("evidence", {}).items():
            evidence_dict[key] = WymiarEvidence(
                wymiar=ev_data.get("wymiar", key),
                znalezione_fragmenty=ev_data.get("znalezione_fragmenty", []),
                czy_obecny=ev_data.get("czy_obecny", False),
                notatki=ev_data.get("notatki"),
            )
        mapped = MappedResponse(evidence=evidence_dict, parsed_response=parsed)

        dim_scores = {}
        for key, ds_data in request.get("dimension_scores", {}).items():
            dim_scores[key] = DimensionScore(
                wymiar=ds_data.get("wymiar", key),
                ocena=ds_data.get("ocena", 0.0),
                waga=ds_data.get("waga", 0.0),
                punkty=ds_data.get("punkty", 0.0),
                uzasadnienie=ds_data.get("uzasadnienie", ""),
            )

        ocena = request.get("ocena", request.get("ocena_delegowanie", 0.0))
        scoring = ScoringResult(
            ocena=ocena,
            poziom=request.get("poziom", ""),
            dimension_scores=dim_scores,
            mapped_response=mapped,
        )
        prompt_sent = fg.prompt_template.format(
            score=scoring.ocena,
            level=scoring.poziom,
            dimension_scores=fg._format_dimension_scores(scoring),
            evidence=fg._format_evidence(scoring),
        )
        feedback = await fg.generate(scoring)
        return {
            "summary": feedback.summary,
            "recommendation": feedback.recommendation,
            "mocne_strony": feedback.mocne_strony,
            "obszary_rozwoju": feedback.obszary_rozwoju,
            "competency": competency,
            "_prompt": {
                "system": "Jesteś ekspertem w udzielaniu rozwojowego feedbacku menedżerom. Zwracasz wyłącznie poprawny JSON.",
                "user": prompt_sent,
            },
            "_prompt_meta": {
                "module": "feedback",
                "competency": competency,
                "active_version": active_prompt.get("version"),
                "active_template": active_prompt.get("content"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# SESSIONS
# ---------------------------------------------------------------------------

class SaveSessionRequest(BaseModel):
    participant_id: str
    steps: dict
    competency: str = "delegowanie"


@app.post("/api/sessions/save")
async def save_session(req: SaveSessionRequest, request: Request):
    """Zapisuje pełną sesję diagnostyczną do pliku JSON."""
    from datetime import datetime
    user = getattr(request.state, "user", {})
    username = user.get("username", "anonymous")

    sessions_dir = Path(__file__).parent.parent / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{req.participant_id}_{username}.json"
    filepath = sessions_dir / filename

    session_data = {
        "saved_at": datetime.now().isoformat(),
        "saved_by": username,
        "participant_id": req.participant_id,
        "competency": req.competency,
        "steps": req.steps,
        "prompt_versions": pm_get_active_versions(req.competency),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)

    return {"ok": True, "filename": filename}


class SaveRunRequest(BaseModel):
    participant_id: str = "P001"
    competency: str
    module: str
    run: dict


@app.post("/api/runs/save")
async def save_run(req: SaveRunRequest, request: Request):
    """Zapisuje pojedynczy run modułu (prompt + wynik) do historii."""
    from datetime import datetime
    user = getattr(request.state, "user", {})
    username = user.get("username", "anonymous")

    runs_dir = Path(__file__).parent.parent / "runs"
    runs_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_module = req.module.replace("/", "_")
    filename = f"{ts}_{req.participant_id}_{req.competency}_{safe_module}_{username}.json"
    filepath = runs_dir / filename

    run_data = {
        "saved_at": datetime.now().isoformat(),
        "saved_by": username,
        "participant_id": req.participant_id,
        "competency": req.competency,
        "module": req.module,
        "run": req.run,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2, ensure_ascii=False)

    return {"ok": True, "filename": filename}


@app.get("/api/runs")
async def list_runs(request: Request, competency: Optional[str] = None, module: Optional[str] = None):
    """Lista zapisanych runów prompt/result z opcjonalnym filtrem."""
    runs_dir = Path(__file__).parent.parent / "runs"
    if not runs_dir.exists():
        return []

    runs = []
    for fp in sorted(runs_dir.glob("*.json"), reverse=True):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if competency and data.get("competency") != competency:
                continue
            if module and data.get("module") != module:
                continue
            runs.append({
                "filename": fp.name,
                "saved_at": data.get("saved_at"),
                "saved_by": data.get("saved_by"),
                "participant_id": data.get("participant_id"),
                "competency": data.get("competency"),
                "module": data.get("module"),
            })
        except Exception:
            continue
    return runs


@app.get("/api/runs/{filename}")
async def get_run_file(filename: str, request: Request):
    """Pobiera pojedynczy zapis runu."""
    runs_dir = Path(__file__).parent.parent / "runs"
    filepath = runs_dir / filename
    if not filepath.exists() or not filepath.name.endswith(".json"):
        raise HTTPException(status_code=404, detail="Run nie znaleziony")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/sessions")
async def list_sessions(request: Request, competency: Optional[str] = None):
    """Lista zapisanych sesji diagnostycznych. Opcjonalny filtr po kompetencji."""
    sessions_dir = Path(__file__).parent.parent / "sessions"
    if not sessions_dir.exists():
        return []

    sessions = []
    for fp in sorted(sessions_dir.glob("*.json"), reverse=True):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            session_competency = data.get("competency", "delegowanie")
            if competency and session_competency != competency:
                continue
            score_data = data.get("steps", {}).get("score", {})
            score = score_data.get("ocena", score_data.get("ocena_delegowanie"))
            sessions.append({
                "filename": fp.name,
                "saved_at": data.get("saved_at"),
                "saved_by": data.get("saved_by"),
                "participant_id": data.get("participant_id"),
                "competency": session_competency,
                "score": score,
            })
        except Exception:
            continue
    return sessions


@app.get("/api/sessions/compare")
async def compare_sessions(a: str, b: str, request: Request):
    """Porównuje dwie sesje diagnostyczne."""
    sessions_dir = Path(__file__).parent.parent / "sessions"

    filepath_a = sessions_dir / a
    filepath_b = sessions_dir / b

    if not filepath_a.exists():
        raise HTTPException(status_code=404, detail=f"Sesja {a} nie znaleziona")
    if not filepath_b.exists():
        raise HTTPException(status_code=404, detail=f"Sesja {b} nie znaleziona")

    with open(filepath_a, "r", encoding="utf-8") as f:
        session_a = json.load(f)
    with open(filepath_b, "r", encoding="utf-8") as f:
        session_b = json.load(f)

    def extract_session_data(session):
        steps = session.get("steps", {})
        score_data = steps.get("score", {})
        feedback_data = steps.get("feedback", {})
        parse_data = steps.get("parse", {})
        map_data = steps.get("map", {})

        ocena = score_data.get("ocena", score_data.get("ocena_delegowanie"))

        return {
            "participant_id": session.get("participant_id"),
            "competency": session.get("competency", "delegowanie"),
            "saved_at": session.get("saved_at"),
            "saved_by": session.get("saved_by"),
            "ocena": ocena,
            "poziom": score_data.get("poziom"),
            "dimension_scores": {
                k: v.get("ocena") for k, v in score_data.get("dimension_scores", {}).items()
            },
            "prompt_versions": steps.get("prompt_versions", {}),
            "prompts": {
                "parse": parse_data.get("_prompt", {}),
                "map": map_data.get("_prompt", {}),
                "score": score_data.get("_prompt", {}),
                "feedback": feedback_data.get("_prompt", {}),
            },
            "feedback": {
                "summary": feedback_data.get("summary"),
                "recommendation": feedback_data.get("recommendation"),
                "mocne_strony": feedback_data.get("mocne_strony", []),
                "obszary_rozwoju": feedback_data.get("obszary_rozwoju", []),
            },
        }

    data_a = extract_session_data(session_a)
    data_b = extract_session_data(session_b)

    score_diff = None
    if data_a["ocena"] is not None and data_b["ocena"] is not None:
        score_diff = round(data_b["ocena"] - data_a["ocena"], 2)

    dimension_diffs = {}
    all_dims = set(list(data_a["dimension_scores"].keys()) + list(data_b["dimension_scores"].keys()))
    for dim in all_dims:
        val_a = data_a["dimension_scores"].get(dim)
        val_b = data_b["dimension_scores"].get(dim)
        if val_a is not None and val_b is not None:
            dimension_diffs[dim] = {"a": val_a, "b": val_b, "diff": round(val_b - val_a, 2)}
        else:
            dimension_diffs[dim] = {"a": val_a, "b": val_b, "diff": None}

    return {
        "session_a": {"filename": a, **data_a},
        "session_b": {"filename": b, **data_b},
        "comparison": {
            "score_diff": score_diff,
            "dimension_diffs": dimension_diffs,
            "same_participant": data_a["participant_id"] == data_b["participant_id"],
            "same_competency": data_a["competency"] == data_b["competency"],
        },
    }


@app.get("/api/sessions/{filename}")
async def get_session_file(filename: str, request: Request):
    """Pobiera konkretną sesję diagnostyczną."""
    sessions_dir = Path(__file__).parent.parent / "sessions"
    filepath = sessions_dir / filename
    if not filepath.exists() or not filepath.name.endswith(".json"):
        raise HTTPException(status_code=404, detail="Sesja nie znaleziona")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# PROMPTS
# ---------------------------------------------------------------------------

@app.get("/api/prompts")
async def list_prompts(request: Request):
    return pm_list_modules()


@app.get("/api/prompts/{module}")
async def get_module_prompts(module: str, request: Request, competency: str = "delegowanie"):
    """Szczegóły modułu + lista wersji."""
    try:
        versions = pm_list_versions(module)
        active = pm_get_prompt(module, competency=competency)
        return {
            "module": module,
            "competency": competency,
            "active_version": active["version"],
            "active_content": active["content"],
            "versions": versions,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/prompts/{module}/{version}")
async def get_prompt_version(module: str, version: str, request: Request):
    try:
        return pm_get_prompt(module, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


class SavePromptRequest(BaseModel):
    version_name: str
    content: str
    description: str = ""
    activate: bool = False
    competency: str = "delegowanie"


@app.post("/api/prompts/{module}")
async def save_prompt_version(module: str, req: SavePromptRequest, request: Request):
    try:
        result = pm_save_prompt(
            module=module,
            version_name=req.version_name,
            content=req.content,
            description=req.description,
            activate=req.activate,
            competency=req.competency,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ActivateVersionRequest(BaseModel):
    version: str
    competency: str = "delegowanie"


@app.put("/api/prompts/{module}/activate")
async def activate_prompt_version(module: str, req: ActivateVersionRequest, request: Request):
    try:
        return pm_activate_version(module, req.version, req.competency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/prompts-active")
async def get_all_active_prompts(request: Request, competency: Optional[str] = None):
    return pm_get_active_versions(competency)


# ---------------------------------------------------------------------------
# DIMENSIONS & WEIGHTS
# ---------------------------------------------------------------------------

@app.get("/dimensions")
async def get_dimensions(competency: str = "delegowanie"):
    """Zwraca definicje wymiarów dla danej kompetencji."""
    if competency not in COMPETENCY_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Kompetencja '{competency}' nie istnieje")
    wymiary = get_wymiary_for_competency(competency)
    dimensions = {}
    for key, value in wymiary.items():
        dimensions[key] = {
            "nazwa": value["nazwa"],
            "opis": value["opis"],
            "poziomy_count": len(value["poziomy"]),
        }
    return {
        "competency": competency,
        "dimensions": dimensions,
        "total_dimensions": len(dimensions),
    }


@app.get("/weights")
async def get_weights(competency: Optional[str] = None):
    """Zwraca wagi wymiarów. Opcjonalnie filtrowane po kompetencji."""
    weights_path = Path(__file__).parent.parent / "config" / "weights.json"
    with open(weights_path, "r", encoding="utf-8") as f:
        weights_data = json.load(f)

    if competency:
        if competency not in weights_data:
            raise HTTPException(status_code=404, detail=f"Brak wag dla kompetencji '{competency}'")
        return {competency: weights_data[competency]}
    return weights_data


@app.put("/api/weights/{competency}")
async def update_weights(competency: str, request: Request):
    """Aktualizuje wagi dla danej kompetencji."""
    if competency not in COMPETENCY_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Kompetencja '{competency}' nie istnieje")

    body = await request.json()
    weights = body.get("weights", body)

    wymiary = get_wymiary_for_competency(competency)
    for key in weights:
        if key not in wymiary:
            raise HTTPException(status_code=400, detail=f"Nieznany wymiar: {key}")

    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        raise HTTPException(status_code=400, detail=f"Suma wag musi wynosić 1.0, jest: {total:.3f}")

    weights_path = Path(__file__).parent.parent / "config" / "weights.json"
    with open(weights_path, "r", encoding="utf-8") as f:
        weights_data = json.load(f)

    weights_data[competency] = weights

    with open(weights_path, "w", encoding="utf-8") as f:
        json.dump(weights_data, f, indent=2, ensure_ascii=False)

    return {"ok": True, "competency": competency, "weights": weights}


# ---------------------------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------------------------

static_dir = Path(__file__).parent / "static"


@app.get("/login")
async def serve_login():
    return FileResponse(str(static_dir / "login.html"))


@app.get("/ui")
async def serve_ui():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/prompts")
async def serve_prompts():
    return FileResponse(str(static_dir / "prompts.html"))


@app.get("/compare")
async def serve_compare():
    return FileResponse(str(static_dir / "compare.html"))


@app.get("/calibration")
async def serve_calibration():
    return FileResponse(str(static_dir / "calibration.html"))


if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
