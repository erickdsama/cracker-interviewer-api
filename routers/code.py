from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
import io
import contextlib

router = APIRouter(prefix="/code", tags=["code"])

class CodeRequest(BaseModel):
    code: str

@router.post("/run")
async def run_code(request: CodeRequest):
    code = request.code
    output = io.StringIO()
    
    try:
        # Capture stdout
        with contextlib.redirect_stdout(output):
            # Use a restricted global scope if needed, but for local dev exec is fine
            exec(code, {"__name__": "__main__"})
            
        return {"output": output.getvalue()}
    except Exception as e:
        return {"output": f"Error: {str(e)}"}
