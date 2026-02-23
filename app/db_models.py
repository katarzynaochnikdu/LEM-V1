import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.database import get_connection


SESSION_REF_PATTERN = re.compile(r"^(?:session_)?(\d+)(?:\.json)?$")
RUN_REF_PATTERN = re.compile(r"^(?:run_)?(\d+)(?:\.json)?$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def _loads(data: Optional[str], default: Any) -> Any:
    if not data:
        return default
    try:
        return json.loads(data)
    except (TypeError, json.JSONDecodeError):
        return default


def _parse_session_ref(ref: str) -> Optional[int]:
    match = SESSION_REF_PATTERN.match(ref.strip())
    return int(match.group(1)) if match else None


def _parse_run_ref(ref: str) -> Optional[int]:
    match = RUN_REF_PATTERN.match(ref.strip())
    return int(match.group(1)) if match else None


def _extract_score_data(steps: dict[str, Any]) -> tuple[Optional[float], Optional[str]]:
    score_data = steps.get("score", {})
    score = score_data.get("ocena", score_data.get("ocena_delegowanie"))
    level = score_data.get("poziom")
    return score, level


async def _fetchone(conn, query: str, params: tuple[Any, ...] = ()) -> Optional[Any]:
    cursor = await conn.execute(query, params)
    return await cursor.fetchone()


async def save_assessment(
    *,
    participant_id: str,
    competency: str,
    steps: dict[str, Any],
    created_by: str,
    prompt_versions: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    score, level = _extract_score_data(steps)
    parse_data = steps.get("parse", {})
    map_data = steps.get("map", {})
    score_data = steps.get("score", {})
    feedback_data = steps.get("feedback", {})

    response_text = parse_data.get("raw_text") or steps.get("response_text") or ""
    llm_model = None
    for step_name in ("score", "feedback", "map", "parse"):
        llm_payload = steps.get(step_name, {}).get("_llm", {})
        if llm_payload and llm_payload.get("model"):
            llm_model = llm_payload.get("model")
            break

    if prompt_versions is None:
        prompt_versions = steps.get("prompt_versions", {})

    total_tokens = 0
    total_cost_usd = 0.0
    for step_name in ("parse", "map", "score", "feedback"):
        step_data = steps.get(step_name, {})
        usage = step_data.get("_usage")
        if usage:
            total_tokens += int(usage.get("total_tokens", 0))
        cost = step_data.get("_cost")
        if isinstance(cost, (int, float)):
            total_cost_usd += float(cost)

    created_at = _now_iso()
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO assessments (
                participant_id, competency, response_text, score, level, created_at, created_by,
                llm_model, prompt_versions, total_tokens, total_cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                participant_id,
                competency,
                response_text,
                score,
                level,
                created_at,
                created_by,
                llm_model,
                _dumps(prompt_versions),
                total_tokens,
                total_cost_usd,
            ),
        )
        assessment_id = cursor.lastrowid

        for dimension, dimension_data in score_data.get("dimension_scores", {}).items():
            await conn.execute(
                """
                INSERT INTO dimension_scores (
                    assessment_id, dimension, score, weight, points, justification
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    dimension,
                    dimension_data.get("ocena"),
                    dimension_data.get("waga"),
                    dimension_data.get("punkty"),
                    dimension_data.get("uzasadnienie"),
                ),
            )

        for dimension, evidence_data in map_data.get("evidence", {}).items():
            citations = evidence_data.get("znalezione_fragmenty", [])
            is_present = 1 if evidence_data.get("czy_obecny") else 0
            if citations:
                for citation in citations:
                    await conn.execute(
                        """
                        INSERT INTO evidence (assessment_id, dimension, citation, is_present)
                        VALUES (?, ?, ?, ?)
                        """,
                        (assessment_id, dimension, citation, is_present),
                    )
            else:
                await conn.execute(
                    """
                    INSERT INTO evidence (assessment_id, dimension, citation, is_present)
                    VALUES (?, ?, ?, ?)
                    """,
                    (assessment_id, dimension, "", is_present),
                )

        await conn.execute(
            """
            INSERT INTO feedback (
                assessment_id, summary, recommendation, strengths, development_areas
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                assessment_id,
                feedback_data.get("summary"),
                feedback_data.get("recommendation"),
                _dumps(feedback_data.get("mocne_strony", [])),
                _dumps(feedback_data.get("obszary_rozwoju", [])),
            ),
        )

        for step_name in ("parse", "map", "score", "feedback"):
            output_data = steps.get(step_name)
            if not output_data:
                continue
            prompt_data = output_data.get("_prompt")
            prompt_meta = output_data.get("_prompt_meta", {})
            await conn.execute(
                """
                INSERT INTO pipeline_steps (
                    assessment_id, step_name, input_data, output_data, prompt_used, prompt_version, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    step_name,
                    None,
                    _dumps(output_data),
                    _dumps(prompt_data) if prompt_data else None,
                    prompt_meta.get("active_version"),
                    None,
                    created_at,
                ),
            )

        await conn.commit()

    return {
        "id": assessment_id,
        "filename": f"session_{assessment_id}.json",
        "saved_at": created_at,
        "saved_by": created_by,
    }


async def save_run(
    *,
    participant_id: str,
    competency: str,
    module: str,
    run: dict[str, Any],
    saved_by: str,
) -> dict[str, Any]:
    created_at = _now_iso()
    prompt = run.get("_prompt")
    prompt_meta = run.get("_prompt_meta", {})

    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO pipeline_steps (
                assessment_id, step_name, input_data, output_data, prompt_used, prompt_version, duration_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                None,
                f"run:{module}",
                _dumps(
                    {
                        "participant_id": participant_id,
                        "competency": competency,
                        "saved_by": saved_by,
                    }
                ),
                _dumps(run),
                _dumps(prompt) if prompt else None,
                prompt_meta.get("active_version"),
                None,
                created_at,
            ),
        )
        run_id = cursor.lastrowid
        await conn.commit()

    return {
        "id": run_id,
        "filename": f"run_{run_id}.json",
        "saved_at": created_at,
        "saved_by": saved_by,
        "participant_id": participant_id,
        "competency": competency,
        "module": module,
    }


async def list_runs(competency: Optional[str] = None, module: Optional[str] = None) -> list[dict[str, Any]]:
    async with get_connection() as conn:
        rows = await conn.execute_fetchall(
            """
            SELECT id, step_name, input_data, created_at
            FROM pipeline_steps
            WHERE step_name LIKE 'run:%'
            ORDER BY id DESC
            """
        )

    result: list[dict[str, Any]] = []
    for row in rows:
        module_name = row["step_name"].replace("run:", "", 1)
        input_data = _loads(row["input_data"], {})
        if competency and input_data.get("competency") != competency:
            continue
        if module and module_name != module:
            continue
        result.append(
            {
                "filename": f"run_{row['id']}.json",
                "saved_at": row["created_at"],
                "saved_by": input_data.get("saved_by"),
                "participant_id": input_data.get("participant_id"),
                "competency": input_data.get("competency"),
                "module": module_name,
            }
        )
    return result


async def get_run_by_ref(run_ref: str) -> Optional[dict[str, Any]]:
    run_id = _parse_run_ref(run_ref)
    if run_id is None:
        return None

    async with get_connection() as conn:
        row = await _fetchone(
            conn,
            """
            SELECT id, step_name, input_data, output_data, created_at
            FROM pipeline_steps
            WHERE id = ? AND step_name LIKE 'run:%'
            """,
            (run_id,),
        )

    if not row:
        return None

    input_data = _loads(row["input_data"], {})
    run_data = _loads(row["output_data"], {})
    module_name = row["step_name"].replace("run:", "", 1)
    return {
        "saved_at": row["created_at"],
        "saved_by": input_data.get("saved_by"),
        "participant_id": input_data.get("participant_id"),
        "competency": input_data.get("competency"),
        "module": module_name,
        "run": run_data,
    }


async def list_assessments(
    competency: Optional[str] = None,
    participant_id: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    query = """
        SELECT id, participant_id, competency, response_text, score, level, created_at, created_by, llm_model,
               total_tokens, total_cost_usd
        FROM assessments
        WHERE 1 = 1
    """
    params: list[Any] = []
    if competency:
        query += " AND competency = ?"
        params.append(competency)
    if participant_id:
        query += " AND participant_id = ?"
        params.append(participant_id)

    safe_limit = max(1, min(limit, 1000))
    query += " ORDER BY id DESC LIMIT ?"
    params.append(safe_limit)

    async with get_connection() as conn:
        rows = await conn.execute_fetchall(query, tuple(params))

    result = []
    for row in rows:
        text = row["response_text"] or ""
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12] if text else ""
        result.append({
            "id": row["id"],
            "filename": f"session_{row['id']}.json",
            "participant_id": row["participant_id"],
            "competency": row["competency"],
            "score": row["score"],
            "level": row["level"],
            "saved_at": row["created_at"],
            "saved_by": row["created_by"],
            "llm_model": row["llm_model"],
            "total_tokens": row["total_tokens"] or 0,
            "total_cost_usd": row["total_cost_usd"] or 0.0,
            "response_text_hash": text_hash,
            "response_text_len": len(text),
        })
    return result


async def get_assessment_by_id(assessment_id: int) -> Optional[dict[str, Any]]:
    async with get_connection() as conn:
        assessment = await _fetchone(
            conn,
            """
            SELECT id, participant_id, competency, response_text, score, level, created_at, created_by,
                   llm_model, prompt_versions, total_tokens, total_cost_usd
            FROM assessments
            WHERE id = ?
            """,
            (assessment_id,),
        )
        if not assessment:
            return None

        dimension_rows = await conn.execute_fetchall(
            """
            SELECT dimension, score, weight, points, justification
            FROM dimension_scores
            WHERE assessment_id = ?
            ORDER BY id ASC
            """,
            (assessment_id,),
        )
        evidence_rows = await conn.execute_fetchall(
            """
            SELECT dimension, citation, is_present
            FROM evidence
            WHERE assessment_id = ?
            ORDER BY id ASC
            """,
            (assessment_id,),
        )
        feedback_row = await _fetchone(
            conn,
            """
            SELECT summary, recommendation, strengths, development_areas
            FROM feedback
            WHERE assessment_id = ?
            """,
            (assessment_id,),
        )
        pipeline_rows = await conn.execute_fetchall(
            """
            SELECT step_name, output_data
            FROM pipeline_steps
            WHERE assessment_id = ?
            ORDER BY id ASC
            """,
            (assessment_id,),
        )

    dimension_scores: dict[str, Any] = {}
    for row in dimension_rows:
        dimension_scores[row["dimension"]] = {
            "wymiar": row["dimension"],
            "ocena": row["score"],
            "waga": row["weight"],
            "punkty": row["points"],
            "uzasadnienie": row["justification"],
        }

    evidence_map: dict[str, list[str]] = {}
    for row in evidence_rows:
        evidence_map.setdefault(row["dimension"], [])
        if row["citation"]:
            evidence_map[row["dimension"]].append(row["citation"])

    steps: dict[str, Any] = {}
    usage_per_step: dict[str, Any] = {}
    for row in pipeline_rows:
        step_out = _loads(row["output_data"], {})
        steps[row["step_name"]] = step_out
        if step_out.get("_usage") or step_out.get("_cost") is not None:
            usage_per_step[row["step_name"]] = {
                "usage": step_out.get("_usage"),
                "cost_usd": step_out.get("_cost"),
            }
    steps["prompt_versions"] = _loads(assessment["prompt_versions"], {})

    feedback_data = dict(feedback_row) if feedback_row else {}
    return {
        "id": assessment["id"],
        "filename": f"session_{assessment['id']}.json",
        "saved_at": assessment["created_at"],
        "saved_by": assessment["created_by"],
        "participant_id": assessment["participant_id"],
        "competency": assessment["competency"],
        "response_text": assessment["response_text"],
        "score": assessment["score"],
        "level": assessment["level"],
        "llm_model": assessment["llm_model"],
        "prompt_versions": _loads(assessment["prompt_versions"], {}),
        "total_tokens": assessment["total_tokens"] or 0,
        "total_cost_usd": assessment["total_cost_usd"] or 0.0,
        "usage_per_step": usage_per_step,
        "steps": steps,
        "evidence": evidence_map,
        "dimension_scores": {k: v.get("ocena") for k, v in dimension_scores.items()},
        "scoring_details": {
            "ocena": assessment["score"],
            "poziom": assessment["level"],
            "dimension_scores": dimension_scores,
        },
        "feedback": {
            "summary": feedback_data.get("summary"),
            "recommendation": feedback_data.get("recommendation"),
            "mocne_strony": _loads(feedback_data.get("strengths"), []),
            "obszary_rozwoju": _loads(feedback_data.get("development_areas"), []),
        },
    }


async def get_assessment_by_ref(assessment_ref: str) -> Optional[dict[str, Any]]:
    assessment_id = _parse_session_ref(assessment_ref)
    if assessment_id is None:
        return None
    return await get_assessment_by_id(assessment_id)


def _extract_session_compare_data(session: dict[str, Any]) -> dict[str, Any]:
    steps = session.get("steps", {})
    score_data = steps.get("score", {})
    feedback_data = steps.get("feedback", {})
    parse_data = steps.get("parse", {})
    map_data = steps.get("map", {})

    score = score_data.get("ocena", score_data.get("ocena_delegowanie"))
    return {
        "participant_id": session.get("participant_id"),
        "competency": session.get("competency", "delegowanie"),
        "saved_at": session.get("saved_at"),
        "saved_by": session.get("saved_by"),
        "ocena": score,
        "poziom": score_data.get("poziom"),
        "dimension_scores": {
            key: value.get("ocena") for key, value in score_data.get("dimension_scores", {}).items()
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


async def compare_assessments(a_ref: str, b_ref: str) -> Optional[dict[str, Any]]:
    session_a = await get_assessment_by_ref(a_ref)
    session_b = await get_assessment_by_ref(b_ref)
    if not session_a or not session_b:
        return None

    data_a = _extract_session_compare_data(session_a)
    data_b = _extract_session_compare_data(session_b)

    score_diff = None
    if data_a["ocena"] is not None and data_b["ocena"] is not None:
        score_diff = round(data_b["ocena"] - data_a["ocena"], 2)

    dimension_diffs: dict[str, Any] = {}
    all_dimensions = set(data_a["dimension_scores"].keys()) | set(data_b["dimension_scores"].keys())
    for dimension in all_dimensions:
        value_a = data_a["dimension_scores"].get(dimension)
        value_b = data_b["dimension_scores"].get(dimension)
        if value_a is not None and value_b is not None:
            diff = round(value_b - value_a, 2)
        else:
            diff = None
        dimension_diffs[dimension] = {"a": value_a, "b": value_b, "diff": diff}

    return {
        "session_a": {"filename": session_a["filename"], **data_a},
        "session_b": {"filename": session_b["filename"], **data_b},
        "comparison": {
            "score_diff": score_diff,
            "dimension_diffs": dimension_diffs,
            "same_participant": data_a["participant_id"] == data_b["participant_id"],
            "same_competency": data_a["competency"] == data_b["competency"],
        },
    }


async def delete_assessment(assessment_id: int) -> bool:
    async with get_connection() as conn:
        row = await _fetchone(conn, "SELECT id FROM assessments WHERE id = ?", (assessment_id,))
        if not row:
            return False

        await conn.execute("DELETE FROM dimension_scores WHERE assessment_id = ?", (assessment_id,))
        await conn.execute("DELETE FROM evidence WHERE assessment_id = ?", (assessment_id,))
        await conn.execute("DELETE FROM feedback WHERE assessment_id = ?", (assessment_id,))
        await conn.execute("DELETE FROM pipeline_steps WHERE assessment_id = ?", (assessment_id,))
        await conn.execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))
        await conn.commit()

    return True


async def delete_assessment_by_ref(assessment_ref: str) -> bool:
    assessment_id = _parse_session_ref(assessment_ref)
    if assessment_id is None:
        return False
    return await delete_assessment(assessment_id)


async def get_assessment_stats() -> dict[str, Any]:
    async with get_connection() as conn:
        total_row = await _fetchone(conn, "SELECT COUNT(*) AS count FROM assessments")
        average_row = await _fetchone(conn, "SELECT AVG(score) AS avg_score FROM assessments")
        competency_rows = await conn.execute_fetchall(
            """
            SELECT competency, COUNT(*) AS count, AVG(score) AS avg_score
            FROM assessments
            GROUP BY competency
            ORDER BY competency ASC
            """
        )
        latest_row = await _fetchone(conn, "SELECT created_at FROM assessments ORDER BY id DESC LIMIT 1")

    return {
        "total_assessments": total_row["count"] if total_row else 0,
        "average_score": round(average_row["avg_score"], 3) if average_row and average_row["avg_score"] is not None else None,
        "by_competency": [
            {
                "competency": row["competency"],
                "count": row["count"],
                "average_score": round(row["avg_score"], 3) if row["avg_score"] is not None else None,
            }
            for row in competency_rows
        ],
        "latest_assessment_at": latest_row["created_at"] if latest_row else None,
    }
