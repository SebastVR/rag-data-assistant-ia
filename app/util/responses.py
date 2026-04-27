from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse


class StandardJSONResponse(JSONResponse):
    """
    A standard JSON response that includes CORS headers.
    This response is used to return JSON data with appropriate CORS headers.
    """

    def __init__(self, data, status_code=200, headers=None):
        content = jsonable_encoder(data)
        if headers is None:
            headers = {}
        headers["Access-Control-Allow-Origin"] = "*"
        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        super().__init__(content, status_code, headers)


class StandardFileResponse(FileResponse):
    """
    A standard file response that includes CORS headers.
    This response is used to return files with appropriate CORS headers.
    """

    def __init__(self, content, status_code=200, headers=None):
        if headers is None:
            headers = {}
        headers["Access-Control-Allow-Origin"] = "*"
        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        super().__init__(content, status_code, headers)


class StandardStreamingResponse(StreamingResponse):
    """
    A standard streaming response that includes CORS headers.
    This response is used to stream data with appropriate CORS headers.
    """

    def __init__(self, content, status_code=200, headers=None):
        if headers is None:
            headers = {}
        headers["Access-Control-Allow-Origin"] = "*"
        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        super().__init__(
            content, status_code, headers, media_type="application/x-ndjson"
        )
