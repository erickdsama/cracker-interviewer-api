from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..services.code import CodeService

router = APIRouter(prefix="/code", tags=["code"])

class CodeRequest(BaseModel):
    code: str

def get_code_service() -> CodeService:
    return CodeService()

@router.post("/run")
async def run_code(request: CodeRequest, code_service: CodeService = Depends(get_code_service)):
    output = code_service.run_code(request.code)
    return {"output": output}
