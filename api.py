"""
REST API for Heritage Connector.

To run: `python api.py`
"""

from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.on_event("startup")
async def startup():
    pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
