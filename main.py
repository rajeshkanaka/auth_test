from fastapi import FastAPI
from routers import auth, chatbot_backend
import uvicorn

app = FastAPI(
    title="EvalAssist - Your Real Estate Assistant by WAIV",
    description="API for authenticating users and handling chatbot queries related to the US property market.",
    version="1.0.0"
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(chatbot_backend.router, prefix="/chatbot", tags=["Chatbot"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)