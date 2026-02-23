"""
FastAPI aplikacja - System Oceny Kompetencji LEM
Obsługa 4 kompetencji menedżerskich z izolowanym cyklem per kompetencja
"""

import json
import logging
import os
import traceback
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
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
    resolve_competency,
    competency_short_name,
    COMPETENCY_REGISTRY,
)
from app.auth import (
    ensure_admin_exists, verify_user, create_session,
    get_session, delete_session, add_user, list_users,
    delete_user, change_password, change_role,
    log_activity, list_activity, list_active_sessions,
    SESSION_COOKIE,
)
from app.prompt_manager import (
    list_modules as pm_list_modules,
    list_versions as pm_list_versions,
    get_prompt as pm_get_prompt,
    save_prompt as pm_save_prompt,
    activate_version as pm_activate_version,
    get_active_versions as pm_get_active_versions,
    get_system_prompt as pm_get_system_prompt,
)
from app.llm_client import get_llm_runtime, set_llm_runtime
from app.cost_calculator import (
    list_model_pricing,
    estimate_evaluation_cost,
    get_estimated_tokens_per_evaluation,
)
from app.exporters import export_report, get_content_type, get_filename
from app.database import init_db
from app.db_models import (
    save_assessment as db_save_assessment,
    list_assessments as db_list_assessments,
    get_assessment_by_ref as db_get_assessment_by_ref,
    get_assessment_by_id as db_get_assessment_by_id,
    compare_assessments as db_compare_assessments,
    get_assessment_stats as db_get_assessment_stats,
    save_run as db_save_run,
    list_runs as db_list_runs,
    get_run_by_ref as db_get_run_by_ref,
)

load_dotenv()

logger = logging.getLogger("lem.api")

app = FastAPI(
    title="System Oceny Kompetencji LEM",
    description="Automatyczna ocena kompetencji menedżerskich z wykorzystaniem AI",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_API_PATHS = {"/health", "/api/health", "/api/auth/login", "/api/auth/logout", "/api/samples"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)
    if path in PUBLIC_API_PATHS or path.startswith("/api/samples"):
        return await call_next(request)
    token = request.cookies.get(SESSION_COOKIE)
    if not token or not get_session(token):
        return JSONResponse(status_code=401, content={"detail": "Nie zalogowano"})
    request.state.user = get_session(token)
    return await call_next(request)


@app.on_event("startup")
async def startup():
    ensure_admin_exists()
    await init_db()


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
        log_activity(action="login_failed", actor=req.username, status="fail")
        raise HTTPException(status_code=401, detail="Nieprawidłowy login lub hasło")
    token = create_session(req.username, role)
    log_activity(action="login", actor=req.username, details={"role": role})
    cookie_secure = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    cookie_samesite = os.getenv("SESSION_COOKIE_SAMESITE", "lax")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=60 * 60 * 12,
        path="/",
    )
    return {"ok": True, "username": req.username, "role": role}


@app.post("/api/auth/logout")
async def api_logout(response: Response, lem_session: Optional[str] = Cookie(None)):
    username = "unknown"
    if lem_session:
        sess = get_session(lem_session)
        if sess:
            username = sess.get("username", "unknown")
        delete_session(lem_session)
    log_activity(action="logout", actor=username)
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


class LlmConfigRequest(BaseModel):
    provider: str = Field(..., description="local | openai")
    model: str = Field(..., min_length=1)
    openai_api_key: Optional[str] = None


@app.post("/api/auth/users")
async def api_add_user(req: AddUserRequest, request: Request):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin może dodawać użytkowników")
    ok = add_user(req.username, req.password, req.role)
    if not ok:
        raise HTTPException(status_code=409, detail="Użytkownik już istnieje")
    log_activity(action="user_add", actor=user["username"], target=req.username, details={"role": req.role})
    return {"ok": True, "username": req.username}


@app.get("/api/auth/users")
async def api_list_users(request: Request):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin")
    return list_users()


@app.delete("/api/auth/users/{username}")
async def api_delete_user(username: str, request: Request):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin może usuwać użytkowników")
    if username == user["username"]:
        raise HTTPException(status_code=400, detail="Nie możesz usunąć samego siebie")
    if not delete_user(username):
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    log_activity(action="user_delete", actor=user["username"], target=username)
    return {"ok": True}


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=4)


@app.put("/api/auth/users/{username}/password")
async def api_change_password(username: str, req: ChangePasswordRequest, request: Request):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin może zmieniać hasła")
    if not change_password(username, req.new_password):
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    log_activity(action="password_change", actor=user["username"], target=username)
    return {"ok": True}


class ChangeRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|user)$")


@app.put("/api/auth/users/{username}/role")
async def api_change_role(username: str, req: ChangeRoleRequest, request: Request):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin może zmieniać role")
    if username == user["username"]:
        raise HTTPException(status_code=400, detail="Nie możesz zmienić własnej roli")
    if not change_role(username, req.role):
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    log_activity(action="role_change", actor=user["username"], target=username, details={"new_role": req.role})
    return {"ok": True}


@app.get("/api/admin/activity")
async def api_admin_activity(request: Request, limit: int = 200):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin")
    return list_activity(limit)


@app.get("/api/admin/sessions")
async def api_admin_sessions(request: Request):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin")
    return list_active_sessions()


@app.get("/api/llm/config")
async def get_llm_config(request: Request):
    return get_llm_runtime()


@app.put("/api/llm/config")
async def update_llm_config(req: LlmConfigRequest, request: Request):
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tylko admin może zmieniać konfigurację LLM")
    try:
        return set_llm_runtime(
            provider=req.provider.strip().lower(),
            model=req.model.strip(),
            openai_api_key=req.openai_api_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# PRICING
# ---------------------------------------------------------------------------

@app.get("/pricing")
async def get_pricing():
    llm_runtime = get_llm_runtime()
    return {
        "models": list_model_pricing(),
        "estimated_tokens_per_evaluation": get_estimated_tokens_per_evaluation(),
        "active_model": llm_runtime.get("model"),
    }


@app.get("/estimate-cost")
async def get_estimate_cost(
    model: Optional[str] = None,
    count: int = 1,
    cached_input_ratio: float = 0.0,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
):
    selected_model = model or get_llm_runtime().get("model", "")
    try:
        return estimate_evaluation_cost(
            model=selected_model,
            count=count,
            cached_input_ratio=cached_input_ratio,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# FACTORY - nowe instancje modułów per kompetencja (bez singletona)
# ---------------------------------------------------------------------------

def get_modules(competency: str = "delegowanie"):
    """Factory: nowe instancje modułów pipeline dla danej kompetencji."""
    competency = resolve_competency(competency)
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

@app.get("/api/health", response_model=HealthResponse)
async def api_health():
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
# SAMPLE RESPONSES - przykładowe odpowiedzi do testowania
# ---------------------------------------------------------------------------

SAMPLE_RESPONSES_DIR = Path(__file__).resolve().parents[1]

@app.get("/api/samples")
async def list_sample_responses():
    """Lista dostępnych przykładowych odpowiedzi testowych"""
    samples = []
    for f in sorted(SAMPLE_RESPONSES_DIR.glob("odpowiedz_*.md")):
        name = f.stem
        label = name.replace("odpowiedz_", "").replace("_", " ").title()
        samples.append({"id": name, "label": label, "filename": f.name})
    return {"samples": samples}


@app.get("/api/samples/{sample_id}")
async def get_sample_response(sample_id: str):
    """Pobierz treść przykładowej odpowiedzi"""
    filepath = SAMPLE_RESPONSES_DIR / f"{sample_id}.md"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found")
    content = filepath.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    title = lines[0].lstrip("# ").strip() if lines else sample_id
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else content
    return {"id": sample_id, "title": title, "content": body}


# ---------------------------------------------------------------------------
# DIAGNOSTIC ENDPOINTS - krok po kroku
# ---------------------------------------------------------------------------

class DiagnosticParseRequest(BaseModel):
    response_text: str = Field(..., min_length=50)
    competency: str = Field(default="delegowanie")


class ExportRequest(BaseModel):
    participant_id: str = Field(default="session")
    generated_at: Optional[str] = Field(default=None)
    response_text: str = Field(default="")
    selected_competencies: List[str] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict)


@app.post("/api/diagnostic/parse")
async def diagnostic_parse(request: DiagnosticParseRequest, http_request: Request):
    """Krok 1: Strukturyzacja odpowiedzi na sekcje"""
    try:
        user = getattr(http_request.state, "user", {})
        log_activity(action="diagnostic_parse", actor=user.get("username", "?"), details={"competency": request.competency})
        parser, _, _, _ = get_modules(request.competency)
        llm_runtime = get_llm_runtime()
        active_prompt = pm_get_prompt("parse", competency=request.competency)
        prompt_sent = parser.prompt_template.format(response_text=request.response_text)
        parsed = await parser.parse(request.response_text)
        return {
            "sections": parsed.sections,
            "raw_text": parsed.raw_text,
            "competency": request.competency,
            "_prompt": {
                "system": parser.system_prompt,
                "user": prompt_sent,
            },
            "_prompt_meta": {
                "module": "parse",
                "competency": request.competency,
                "active_version": active_prompt.get("version"),
                "active_template": active_prompt.get("content"),
            },
            "_llm": llm_runtime,
        }
    except Exception as e:
        logger.error("diagnostic_parse FAILED:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagnostic/map")
async def diagnostic_map(request: dict, http_request: Request):
    """Krok 2: Ekstrakcja dowodów dla wymiarów"""
    try:
        competency = request.get("competency", "delegowanie")
        user = getattr(http_request.state, "user", {})
        log_activity(action="diagnostic_map", actor=user.get("username", "?"), details={"competency": competency})
        _, mapper, _, _ = get_modules(competency)
        llm_runtime = get_llm_runtime()
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
                "system": mapper.system_prompt,
                "user": prompt_sent,
            },
            "_prompt_meta": {
                "module": "map",
                "competency": competency,
                "active_version": active_prompt.get("version"),
                "active_template": active_prompt.get("content"),
            },
            "_llm": llm_runtime,
        }
    except Exception as e:
        logger.error("diagnostic_map FAILED:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagnostic/score")
async def diagnostic_score(request: dict, http_request: Request):
    """Krok 3: Scoring - ocena wymiarów i wynik końcowy"""
    try:
        competency = request.get("competency", "delegowanie")
        user = getattr(http_request.state, "user", {})
        log_activity(action="diagnostic_score", actor=user.get("username", "?"), details={"competency": competency})
        _, _, scorer, _ = get_modules(competency)
        llm_runtime = get_llm_runtime()
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
                "system": scorer.system_prompt,
                "per_dimension": score_prompts,
            },
            "_prompt_meta": {
                "module": "score",
                "competency": competency,
                "active_version": active_prompt.get("version"),
                "active_template": active_prompt.get("content"),
            },
            "_llm": llm_runtime,
        }
    except Exception as e:
        logger.error("diagnostic_score FAILED:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagnostic/feedback")
async def diagnostic_feedback(request: dict, http_request: Request):
    """Krok 4: Generowanie feedbacku rozwojowego"""
    try:
        competency = request.get("competency", "delegowanie")
        user = getattr(http_request.state, "user", {})
        log_activity(action="diagnostic_feedback", actor=user.get("username", "?"), details={"competency": competency})
        _, _, _, fg = get_modules(competency)
        llm_runtime = get_llm_runtime()
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
                "system": fg.system_prompt,
                "user": prompt_sent,
            },
            "_prompt_meta": {
                "module": "feedback",
                "competency": competency,
                "active_version": active_prompt.get("version"),
                "active_template": active_prompt.get("content"),
            },
            "_llm": llm_runtime,
        }
    except Exception as e:
        logger.error("diagnostic_feedback FAILED:\n%s", traceback.format_exc())
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
    """Zapisuje pełną sesję diagnostyczną do bazy SQLite."""
    try:
        user = getattr(request.state, "user", {})
        username = user.get("username", "anonymous")
        result = await db_save_assessment(
            participant_id=req.participant_id,
            competency=req.competency,
            steps=req.steps,
            created_by=username,
            prompt_versions=pm_get_active_versions(req.competency),
        )
        log_activity(
            action="session_save",
            actor=username,
            details={"participant": req.participant_id, "competency": req.competency, "session_id": result["id"]},
        )
        return {"ok": True, "filename": result["filename"], "id": result["id"]}
    except Exception as e:
        logger.error("save_session FAILED:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


class SaveRunRequest(BaseModel):
    participant_id: str = "P001"
    competency: str
    module: str
    run: dict


@app.post("/api/runs/save")
async def save_run(req: SaveRunRequest, request: Request):
    """Zapisuje pojedynczy run modułu (prompt + wynik) do bazy SQLite."""
    try:
        user = getattr(request.state, "user", {})
        username = user.get("username", "anonymous")
        result = await db_save_run(
            participant_id=req.participant_id,
            competency=req.competency,
            module=req.module,
            run=req.run,
            saved_by=username,
        )
        log_activity(
            action="run_save",
            actor=username,
            details={"participant": req.participant_id, "competency": req.competency, "module": req.module},
        )
        return {"ok": True, "filename": result["filename"], "id": result["id"]}
    except Exception as e:
        logger.error("save_run FAILED:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs")
async def list_runs(request: Request, competency: Optional[str] = None, module: Optional[str] = None):
    """Lista zapisanych runów prompt/result z opcjonalnym filtrem."""
    return await db_list_runs(competency=competency, module=module)


@app.get("/api/runs/{filename}")
async def get_run_file(filename: str, request: Request):
    """Pobiera pojedynczy zapis runu z bazy SQLite."""
    run_data = await db_get_run_by_ref(filename)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run nie znaleziony")
    return run_data


@app.get("/api/sessions")
async def list_sessions(request: Request, competency: Optional[str] = None):
    """Lista zapisanych sesji diagnostycznych. Opcjonalny filtr po kompetencji."""
    return await db_list_assessments(competency=competency)


@app.get("/api/sessions/compare")
async def compare_sessions(a: str, b: str, request: Request):
    """Porównuje dwie sesje diagnostyczne."""
    result = await db_compare_assessments(a, b)
    if not result:
        raise HTTPException(status_code=404, detail="Jedna z sesji nie znaleziona")
    return result


@app.get("/api/sessions/{filename}")
async def get_session_file(filename: str, request: Request):
    """Pobiera konkretną sesję diagnostyczną z bazy SQLite."""
    session_data = await db_get_assessment_by_ref(filename)
    if not session_data:
        raise HTTPException(status_code=404, detail="Sesja nie znaleziona")
    return session_data


@app.get("/api/db/assessments")
async def list_db_assessments(
    request: Request,
    competency: Optional[str] = None,
    participant_id: Optional[str] = None,
    limit: int = 200,
):
    """Lista ocen z bazy danych z opcjonalnym filtrowaniem."""
    return await db_list_assessments(
        competency=competency,
        participant_id=participant_id,
        limit=limit,
    )


@app.get("/api/db/assessments/{assessment_id}")
async def get_db_assessment(assessment_id: int, request: Request):
    """Szczegóły pojedynczej oceny z bazy danych."""
    assessment = await db_get_assessment_by_id(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Ocena nie znaleziona")
    return assessment


@app.get("/api/db/stats")
async def get_db_stats(request: Request):
    """Statystyki bazy danych ocen."""
    return await db_get_assessment_stats()


# ---------------------------------------------------------------------------
# COMPETENCY DEFINITIONS (editable rubric)
# ---------------------------------------------------------------------------

@app.get("/api/competencies")
async def list_competencies(request: Request):
    """Zwraca listę kompetencji z ich metadanymi."""
    from app.rubric import COMPETENCY_REGISTRY
    result = []
    for comp_id, comp in COMPETENCY_REGISTRY.items():
        result.append({
            "id": comp_id,
            "short_id": competency_short_name(comp_id),
            "nazwa": comp["nazwa"],
            "wymiary_count": len(comp["wymiary"]),
            "algorytm_steps": len(comp["algorytm"]),
            "version": comp.get("_version", "1.0"),
            "source": comp.get("_source", ""),
        })
    return result


@app.get("/api/competencies/{competency_id}")
async def get_competency_definition(competency_id: str, request: Request):
    """Zwraca pełną definicję kompetencji (wymiary, algorytm, poziomy)."""
    try:
        full_id = resolve_competency(competency_id)
        info = get_competency_info(full_id)
        wymiary_out = {}
        for key, wym in info["wymiary"].items():
            wymiary_out[key] = {
                "nazwa": wym["nazwa"],
                "opis": wym["opis"],
                "poziomy": {
                    str(lvl): {"opis": data["opis"], "zachowania": data["zachowania"]}
                    for lvl, data in wym["poziomy"].items()
                },
            }
        return {
            "id": full_id,
            "short_id": competency_short_name(full_id),
            "nazwa": info["nazwa"],
            "algorytm": info["algorytm"],
            "wymiary": wymiary_out,
            "version": info.get("_version", "1.0"),
            "source": info.get("_source", ""),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/api/competencies/{competency_id}")
async def update_competency_definition(competency_id: str, req: dict, request: Request):
    """Zapisuje zmodyfikowaną definicję kompetencji."""
    from app.rubric import save_competency_definition
    try:
        full_id = resolve_competency(competency_id)
        wymiary_in = {}
        for key, wym in req.get("wymiary", {}).items():
            wymiary_in[key] = {
                "nazwa": wym["nazwa"],
                "opis": wym["opis"],
                "poziomy": {
                    float(lvl): {"opis": data["opis"], "zachowania": data["zachowania"]}
                    for lvl, data in wym["poziomy"].items()
                },
            }
        data = {
            "nazwa": req.get("nazwa", ""),
            "algorytm": req.get("algorytm", []),
            "wymiary": wymiary_in,
            "version": req.get("version", "1.0"),
            "source": req.get("source", "4 LEM.pdf"),
        }
        user = getattr(request.state, "user", {})
        log_activity(action="update_competency_def", actor=user.get("username", "?"), details={"competency": full_id})
        result = save_competency_definition(full_id, data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# PROMPTS
# ---------------------------------------------------------------------------

@app.get("/api/prompts")
async def list_prompts(request: Request):
    return pm_list_modules()


@app.get("/api/prompts/{module}")
async def get_module_prompts(module: str, request: Request, competency: str = "delegowanie"):
    """Szczegóły modułu + lista wersji filtrowana per kompetencja."""
    try:
        all_versions = pm_list_versions(module)
        short = competency_short_name(resolve_competency(competency))
        filtered = [
            v for v in all_versions
            if short in v.get("active_for", []) or not v.get("active_for")
        ]
        active = pm_get_prompt(module, competency=competency)
        return {
            "module": module,
            "competency": competency,
            "system_prompt": pm_get_system_prompt(module),
            "active_version": active["version"],
            "active_content": active["content"],
            "versions": filtered,
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


@app.post("/api/export/{export_format}")
async def export_results(export_format: str, request: ExportRequest):
    supported_formats = {"json", "txt", "html", "excel", "pdf_full", "pdf_summary"}
    if export_format not in supported_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Nieobslugiwany format '{export_format}'. Dostepne: {sorted(supported_formats)}",
        )

    if not request.results:
        raise HTTPException(status_code=400, detail="Brak wynikow do eksportu")

    try:
        payload = request.model_dump()
        file_bytes = export_report(export_format, payload)
        filename = get_filename(export_format, request.participant_id, request.generated_at)
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return Response(content=file_bytes, media_type=get_content_type(export_format), headers=headers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blad eksportu: {str(e)}")


# ---------------------------------------------------------------------------
# FRONTEND SPA
# ---------------------------------------------------------------------------

FRONTEND_DIST_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def _resolve_frontend_file(requested_path: str) -> Optional[Path]:
    if not FRONTEND_DIST_DIR.exists():
        return None
    candidate = (FRONTEND_DIST_DIR / requested_path).resolve()
    try:
        candidate.relative_to(FRONTEND_DIST_DIR.resolve())
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Nie znaleziono endpointu API")

    # Serve real frontend assets first (js/css/images/etc), then SPA shell.
    requested = full_path.lstrip("/")
    if requested:
        asset_file = _resolve_frontend_file(requested)
        if asset_file:
            return FileResponse(str(asset_file))

    index_file = _resolve_frontend_file("index.html")
    if not index_file:
        raise HTTPException(
            status_code=503,
            detail="Frontend build not found. Build React app in ../frontend (npm run build).",
        )
    return FileResponse(str(index_file))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
