from fastapi import FastAPI
from openpuc_scrapers.server.routes import register_routes

from fastapi.staticfiles import StaticFiles


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This function allows for more flexible app creation and testing.
    """
    app = FastAPI()

    # Mount static files
    app.mount(
        "/",
        StaticFiles(directory="openpuc_scrapers/server/static", html=True),
        name="static",
    )

    return app


# Create the FastAPI application
app = create_app()

# Register all routes
register_routes(app)
