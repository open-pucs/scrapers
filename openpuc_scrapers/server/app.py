from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This function allows for more flexible app creation and testing.
    """
    app = FastAPI()

    # Mount static files
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app
