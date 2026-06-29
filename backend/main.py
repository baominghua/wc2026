from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import teams, matches, predictions, players, injuries, live, auth, reviews, tournament
from services.auth import AuthMiddleware
from services.live_match_feed import start_live_sync_task, stop_live_sync_task

app = FastAPI(
    title="World Cup 2026 Prediction API",
    description="2026美加墨世界杯预测与数据分析API",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["Prediction Reviews"])


# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(teams.router, prefix="/api/v1/teams", tags=["球队"])
app.include_router(matches.router, prefix="/api/v1/matches", tags=["比赛"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["预测"])
app.include_router(players.router, prefix="/api/v1/players", tags=["球员"])
app.include_router(injuries.router, prefix="/api/v1/injuries", tags=["伤停"])
app.include_router(live.router, prefix="/api/v1/live", tags=["实时数据"])
app.include_router(tournament.router, prefix="/api/v1/tournament", tags=["Tournament Projection"])


@app.on_event("startup")
async def startup_event():
    start_live_sync_task()


@app.on_event("shutdown")
async def shutdown_event():
    stop_live_sync_task()

@app.get("/")
async def root():
    return {
        "message": "World Cup 2026 Prediction API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
