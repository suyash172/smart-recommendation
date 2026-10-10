from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.request import RetryRecommendationRequest
from app.schemas.response import RetryRecommendationResponse

router = APIRouter(tags=["Decision Engine"])


@router.post(
    "/retry-decision",
    response_model=RetryRecommendationResponse,
    responses={
        400: {"description": "Invalid input payload"},
        429: {"model": RetryRecommendationResponse, "description": "Circuit breaker: max retry limit reached"},
    },
)
def retry_decision(payload: RetryRecommendationRequest, request: Request):
    response, status_code = request.app.state.decision_service.process(payload)
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))