"""HTTP REST server for regex-vault."""

import logging
import time
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from regexvault.engine import Engine
from regexvault.registry import load_registry, PatternRegistry
from regexvault.models import RedactionStrategy

logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "regexvault_requests_total",
    "Total requests",
    ["endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "regexvault_request_duration_seconds",
    "Request duration in seconds",
    ["endpoint"],
)
PATTERN_MATCHES = Counter(
    "regexvault_pattern_matches_total",
    "Total pattern matches",
    ["namespace", "pattern_id"],
)


# Request/Response models
class FindRequest(BaseModel):
    """Request model for /find endpoint."""

    text: str
    namespaces: Optional[list[str]] = None
    options: Optional[dict[str, Any]] = Field(default_factory=dict)


class ValidateRequest(BaseModel):
    """Request model for /validate endpoint."""

    text: str
    ns_id: str


class RedactRequest(BaseModel):
    """Request model for /redact endpoint."""

    text: str
    namespaces: Optional[list[str]] = None
    strategy: Optional[str] = "mask"


class FindResponse(BaseModel):
    """Response model for /find endpoint."""

    hits: list[dict[str, Any]]
    count: int
    namespaces_searched: list[str]


class ValidateResponse(BaseModel):
    """Response model for /validate endpoint."""

    ok: bool
    ns_id: str


class RedactResponse(BaseModel):
    """Response model for /redact endpoint."""

    text: str
    redaction_count: int
    strategy: str


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: str
    version: str
    patterns_loaded: int
    namespaces: list[str]


class ReloadResponse(BaseModel):
    """Response model for /reload endpoint."""

    status: str
    version: int
    patterns_loaded: int


class RegexVaultServer:
    """Server wrapper for managing state."""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize server with configuration."""
        self.config = config or {}
        self.registry: Optional[PatternRegistry] = None
        self.engine: Optional[Engine] = None
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load patterns from configuration."""
        registry_config = self.config.get("registry", {})
        paths = registry_config.get("paths")

        logger.info(f"Loading patterns from: {paths}")
        self.registry = load_registry(paths=paths)
        self.engine = Engine(
            self.registry,
            default_mask_char=self.config.get("redaction", {}).get("mask_char", "*"),
            hash_algorithm=self.config.get("redaction", {}).get("hash_algorithm", "sha256"),
        )
        logger.info(f"Loaded {len(self.registry)} patterns")

    def reload_patterns(self) -> dict[str, Any]:
        """Reload patterns from files."""
        try:
            old_version = self.registry.version if self.registry else 0
            self._load_patterns()
            return {
                "status": "ok",
                "version": self.registry.version if self.registry else 0,
                "patterns_loaded": len(self.registry) if self.registry else 0,
                "message": f"Reloaded successfully (v{old_version} -> v{self.registry.version})",
            }
        except Exception as e:
            logger.error(f"Failed to reload patterns: {e}")
            raise HTTPException(status_code=500, detail=f"Reload failed: {str(e)}")


def create_app(config: Optional[dict[str, Any]] = None) -> FastAPI:
    """
    Create FastAPI application.

    Args:
        config: Server configuration dictionary

    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="regex-vault",
        description="PII detection and redaction service",
        version="0.1.0",
    )

    # Create server instance
    server = RegexVaultServer(config)

    # Middleware for metrics and timing
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Any) -> Response:
        """Record metrics for each request."""
        start_time = time.time()
        endpoint = request.url.path

        response = await call_next(request)

        duration = time.time() - start_time
        REQUEST_COUNT.labels(endpoint=endpoint, status=response.status_code).inc()
        REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)

        return response

    @app.post("/find", response_model=FindResponse)
    async def find(request: FindRequest) -> FindResponse:
        """Find PII in text."""
        if server.engine is None:
            raise HTTPException(status_code=500, detail="Engine not initialized")

        try:
            result = server.engine.find(
                request.text,
                namespaces=request.namespaces,
                allow_overlaps=request.options.get("allow_overlaps", False),
                include_matched_text=request.options.get("include_matched_text", False),
            )

            # Record pattern matches
            for match in result.matches:
                PATTERN_MATCHES.labels(
                    namespace=match.namespace,
                    pattern_id=match.pattern_id,
                ).inc()

            hits = [
                {
                    "ns_id": m.ns_id,
                    "pattern_id": m.pattern_id,
                    "namespace": m.namespace,
                    "category": m.category.value,
                    "span": m.span,
                    "match": m.matched_text,
                    "severity": m.severity.value,
                }
                for m in result.matches
            ]

            return FindResponse(
                hits=hits,
                count=result.match_count,
                namespaces_searched=result.namespaces_searched,
            )
        except Exception as e:
            logger.error(f"Find error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/validate", response_model=ValidateResponse)
    async def validate(request: ValidateRequest) -> ValidateResponse:
        """Validate text against pattern."""
        if server.engine is None:
            raise HTTPException(status_code=500, detail="Engine not initialized")

        try:
            result = server.engine.validate(request.text, request.ns_id)
            return ValidateResponse(
                ok=result.is_valid,
                ns_id=request.ns_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Validate error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/redact", response_model=RedactResponse)
    async def redact(request: RedactRequest) -> RedactResponse:
        """Redact PII from text."""
        if server.engine is None:
            raise HTTPException(status_code=500, detail="Engine not initialized")

        try:
            strategy = RedactionStrategy(request.strategy or "mask")
            result = server.engine.redact(
                request.text,
                namespaces=request.namespaces,
                strategy=strategy,
            )

            return RedactResponse(
                text=result.redacted_text,
                redaction_count=result.redaction_count,
                strategy=result.strategy.value,
            )
        except Exception as e:
            logger.error(f"Redact error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Health check endpoint."""
        if server.registry is None:
            raise HTTPException(status_code=503, detail="Registry not initialized")

        return HealthResponse(
            status="healthy",
            version="0.1.0",
            patterns_loaded=len(server.registry),
            namespaces=list(server.registry.namespaces.keys()),
        )

    @app.post("/reload", response_model=ReloadResponse)
    async def reload() -> ReloadResponse:
        """Reload patterns from files."""
        result = server.reload_patterns()
        return ReloadResponse(**result)

    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


# For running directly with uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
