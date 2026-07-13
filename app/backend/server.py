"""FastAPI application and single-process production entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.backend.artifacts import (
    ArtifactValidationError,
    DashboardSnapshot,
    load_snapshot,
)
from app.backend.attack_presets import run_attack
from app.backend.live import LiveNarrativeService
from app.backend.schemas import GuardrailDemoRequest, LiveNarrativeRequest
from app.backend.settings import DashboardSettings
from src.provenance import sha256_file


BUILD_COMMAND = "cd app/frontend && npm ci && npm run build"


def _error(code: str, message: str, details=None) -> dict:
    return {"code": code, "message": message, "details": details}


def _frontend_version(dist: Path) -> str:
    index = dist / "index.html"
    return sha256_file(index)[:12] if index.exists() else "not-built"


def _detector_result(row) -> dict:
    raw = dict(row)
    public = {
        "group": raw["group"],
        "n_seeds": 5,
        "auc_pr_mean": raw.get("test_auc_pr_mean"),
        "auc_pr_std": raw.get("test_auc_pr_std"),
        "roc_auc_mean": raw.get("test_roc_auc_mean"),
        "roc_auc_std": raw.get("test_roc_auc_std"),
        "precision_mean": raw.get("test_precision_mean"),
        "precision_std": raw.get("test_precision_std"),
        "recall_mean": raw.get("test_recall_mean"),
        "recall_std": raw.get("test_recall_std"),
        "f1_mean": raw.get("test_f1_mean"),
        "f1_std": raw.get("test_f1_std"),
        "precision_at_100_mean": raw.get("test_precision_at_100_mean"),
        "precision_at_100_std": raw.get("test_precision_at_100_std"),
        "recall_at_100_mean": raw.get("test_recall_at_100_mean"),
        "recall_at_100_std": raw.get("test_recall_at_100_std"),
        "false_positives_mean": raw.get("test_fp_mean"),
        "false_positives_std": raw.get("test_fp_std"),
        "false_negatives_mean": raw.get("test_fn_mean"),
        "false_negatives_std": raw.get("test_fn_std"),
        "inference_time_seconds_mean": raw.get("test_inference_seconds_mean"),
        "inference_time_seconds_std": raw.get("test_inference_seconds_std"),
    }
    return {key: value for key, value in public.items() if value is not None}


def _rate_estimate(block: dict) -> dict:
    low, high = block["ci95"]
    return {
        "rate": block["rate"],
        "n": block["n"],
        "ci_low": low,
        "ci_high": high,
        **({"by_construction": True} if block.get("by_construction") else {}),
    }


def _explanation_arm(arm: str, faithfulness: dict) -> dict:
    recorded = faithfulness["arms"][arm]
    off = recorded["off_policy_prevalence"]
    delivery = recorded["on_policy_delivery"]
    unavailable = recorded["llm_transport_unavailable"]
    return {
        "arm": arm,
        "format": _rate_estimate(off["detected_format_violation"]),
        "completeness": _rate_estimate(off["detected_completeness_violation"]),
        "grounding": _rate_estimate(off["detected_grounding_violation"]),
        "direction": _rate_estimate(off["detected_direction_violation"]),
        "any_detected_violation": _rate_estimate(off["detected_any_violation"]),
        "fallback": _rate_estimate(delivery["fallback"]),
        "mean_latency_seconds": delivery["mean_latency_seconds"],
        "llm_transport_unavailable_count": round(unavailable["rate"] * unavailable["n"]),
    }


def create_app(
    settings: DashboardSettings,
    snapshot: DashboardSnapshot | None = None,
    *,
    live_service: LiveNarrativeService | None = None,
    require_frontend: bool = True,
) -> FastAPI:
    snapshot = snapshot or load_snapshot(settings)
    dist = settings.frontend_dist
    if require_frontend and not (dist / "index.html").is_file():
        raise RuntimeError(
            f"frontend production build is missing; run: {BUILD_COMMAND}"
        )
    live = live_service or LiveNarrativeService(settings, snapshot)
    app = FastAPI(title="Fraud Detection FYP Demo", version="1.0.0")
    app.state.settings = settings
    app.state.snapshot = snapshot
    app.state.live = live

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=_error(
                "request_validation_error",
                "Invalid API request",
                jsonable_encoder(error.errors()),
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, error: HTTPException):
        detail = error.detail
        if isinstance(detail, dict) and {"code", "message"}.issubset(detail):
            payload = _error(detail["code"], detail["message"], detail.get("details"))
        else:
            payload = _error("http_error", str(detail))
        return JSONResponse(status_code=error.status_code, content=payload)

    @app.get("/api/v1/health")
    def health():
        return {
            "status": "ready",
            "artifact_ready": True,
            "frontend_build_version": _frontend_version(dist),
            "ollama_status": live.availability(),
        }

    @app.get("/api/v1/provenance")
    def provenance():
        return snapshot.public_provenance()

    @app.get("/api/v1/demo-scenarios")
    def scenarios():
        return {"scenarios": [dict(item) for item in snapshot.scenarios]}

    @app.get("/api/v1/cases")
    def cases(
        risk_bucket: Literal["High", "Medium", "Low"] | None = None,
        historical_label: int | None = Query(default=None, ge=0, le=1),
        recorded_fallback: bool | None = None,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
    ):
        selected = list(snapshot.cases.values())
        if risk_bucket is not None:
            selected = [case for case in selected if case.risk_bucket == risk_bucket]
        if historical_label is not None:
            selected = [case for case in selected if case.y_true == historical_label]
        if recorded_fallback is not None:
            selected = [
                case for case in selected if case.narrative.fallback is recorded_fallback
            ]
        selected.sort(key=lambda case: (-case.score, case.case_id))
        return {
            "items": [case.queue_item() for case in selected[offset : offset + limit]],
            "total": len(selected),
            "offset": offset,
            "limit": limit,
            "provenance": snapshot.public_provenance(),
        }

    @app.get("/api/v1/cases/{case_id}")
    def case_detail(case_id: int):
        try:
            detail = snapshot.case(case_id).public_detail()
            detail["provenance"] = snapshot.public_provenance()
            return detail
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail={"code": "case_not_found", "message": str(error)},
            ) from error

    @app.get("/api/v1/results")
    def results():
        faithfulness = dict(snapshot.faithfulness)
        provenance = snapshot.public_provenance()
        return {
            "detector_results": [_detector_result(row) for row in snapshot.detector_results],
            "detector_result_rows": [dict(row) for row in snapshot.result_rows],
            "explanation_results": {
                "explained_cases": len(snapshot.cases),
                "recorded_narrative_arm": settings.config.recorded_narrative_arm,
                "g4_run_id": provenance["g4"]["run_id"],
                "g5_run_id": provenance["g5"]["run_id"],
                "strict": _explanation_arm("strict", faithfulness),
                "simple": _explanation_arm("simple", faithfulness),
                "faithfulness": faithfulness,
            },
            "figures": [
                {
                    "id": "pr_curves",
                    "title": "Recorded precision-recall curves",
                    "caption": "Task 7.1 allowlisted seed-42 detector curves.",
                },
                {
                    "id": "shap_global_bar",
                    "title": "Recorded global SHAP importance",
                    "caption": "G4 recorded global mean absolute SHAP contributions.",
                },
            ],
            "provenance": {
                "results_manifest_sha256": provenance["results"]["manifest_sha256"],
                "source_run_ids": [
                    provenance["detector"]["run_id"],
                    provenance["g4"]["run_id"],
                    provenance["g5"]["run_id"],
                ],
            },
        }

    @app.get("/api/v1/figures/{figure_id}")
    def figure(figure_id: str):
        path = snapshot.figures.get(figure_id)
        if path is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "figure_not_found",
                    "message": "Unknown recorded figure identifier",
                },
            )
        return FileResponse(path, media_type="image/png", filename=f"{figure_id}.png")

    @app.post("/api/v1/live/narrative")
    def live_narrative(request: LiveNarrativeRequest):
        try:
            payload = live.generate(request.case_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail={"code": "case_not_found", "message": str(error)},
            ) from error
        payload["evidence_provenance"] = snapshot.public_provenance()["g4"]
        return JSONResponse(payload, headers={"Cache-Control": "no-store"})

    @app.post("/api/v1/guardrails/demo")
    def guardrail_demo(request: GuardrailDemoRequest):
        try:
            payload = run_attack(snapshot, request.case_id, request.preset)
            payload["provenance"] = {
                "g4": snapshot.public_provenance()["g4"],
                "g5": snapshot.public_provenance()["g5"],
            }
            return payload
        except KeyError as error:
            raise HTTPException(
                status_code=404,
                detail={"code": "case_not_found", "message": str(error)},
            ) from error
        except (RuntimeError, ValueError) as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "invalid_attack_case", "message": str(error)},
            ) from error

    if (dist / "index.html").is_file():
        assets = dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(
                    status_code=404,
                    detail={"code": "api_not_found", "message": "Unknown API endpoint"},
                )
            return FileResponse(dist / "index.html", media_type="text/html")

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    arguments = parser.parse_args()
    settings = DashboardSettings.load(arguments.config)
    try:
        snapshot = load_snapshot(settings)
        app = create_app(settings, snapshot, require_frontend=True)
    except (ArtifactValidationError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    uvicorn.run(
        app,
        host=settings.config.server.host,
        port=settings.config.server.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
