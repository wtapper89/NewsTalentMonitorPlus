from app.config import load_config


if __name__ == "__main__":
    import uvicorn

    config = load_config()
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        timeout_graceful_shutdown=2,
    )
