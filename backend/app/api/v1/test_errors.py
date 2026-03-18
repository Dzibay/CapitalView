from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/test-error", tags=["test-errors"])


@router.get("/500")
async def test_500():
    # Намеренно кидаем ошибку для проверки обработки 500.
    raise HTTPException(status_code=500, detail="Test 500 error")


@router.get("/503")
async def test_503():
    # Намеренно кидаем ошибку для проверки обработки 503.
    raise HTTPException(status_code=503, detail="Test 503 error")

