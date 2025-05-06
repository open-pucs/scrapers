from fastapi import FastAPI, Request
from openpuc_scrapers.server.routes import register_routes
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import traceback


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This function allows for more flexible app creation and testing.
    """
    app = FastAPI()
    register_routes(app)

    # Mount static files
    app.mount(
        "/",
        StaticFiles(directory="openpuc_scrapers/server/static", html=True),
        name="static",
    )

    # Add global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_trace = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": str(exc),
                "trace": error_trace.split("\n"),
            },
        )

    return app


# Create the FastAPI application
app = create_app()
