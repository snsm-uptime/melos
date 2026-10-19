"""MCP Server for Melos.

Provides tools for recipe management, cart operations, and AI-assisted features.
Runs as a separate service on port 9000 for security isolation.
"""
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Melos MCP", version="0.1.0")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mcp",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Melos MCP Service", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 9000))
    uvicorn.run(app, host="0.0.0.0", port=port)
