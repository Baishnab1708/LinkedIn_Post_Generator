from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.post import router as post_router

# Create FastAPI app
app = FastAPI(
    title="LinkedIn Post Generator",
    description="Generate LinkedIn posts with intelligent memory management",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(post_router, prefix="/api", tags=["posts"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "LinkedIn Post Generator API is running"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "api": "operational",
            "memory": "operational"
        }
    }
