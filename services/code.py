import io
import contextlib
import builtins

class CodeService:
    def _is_safe_code(self, code: str) -> bool:
        # Basic keyword blocking
        dangerous_keywords = [
            "import os", "from os", "import sys", "from sys", 
            "import subprocess", "from subprocess", 
            "exec(", "eval(", "open(", "__import__"
        ]
        for keyword in dangerous_keywords:
            if keyword in code:
                return False
        return True

    def run_code(self, code: str) -> str:
        if not self._is_safe_code(code):
            return "Error: Security violation. Dangerous keywords detected."

        output = io.StringIO()
        try:
            # Capture stdout
            with contextlib.redirect_stdout(output):
                # Restricted globals
                safe_globals = {
                    "__name__": "__main__",
                    "__builtins__": {
                        "print": builtins.print,
                        "range": builtins.range,
                        "len": builtins.len,
                        "int": builtins.int,
                        "str": builtins.str,
                        "list": builtins.list,
                        "dict": builtins.dict,
                        "set": builtins.set,
                        "bool": builtins.bool,
                        "float": builtins.float,
                        "sum": builtins.sum,
                        "min": builtins.min,
                        "max": builtins.max,
                        "abs": builtins.abs,
                        "round": builtins.round,
                        "sorted": builtins.sorted,
                        "enumerate": builtins.enumerate,
                        "zip": builtins.zip,
                        "map": builtins.map,
                        "filter": builtins.filter,
                    }
                }
                exec(code, safe_globals)
                
            return output.getvalue()
        except Exception as e:
            return f"Error: {str(e)}"
