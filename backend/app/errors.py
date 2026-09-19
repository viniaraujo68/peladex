from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code, {"code": code, "message": message})


def error_body(code: str, message: str) -> dict:
    return {"detail": {"code": code, "message": message}}
