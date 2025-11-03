from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from service.db_service import SQLiteDatabase
from service.dependencies import with_settings
from service.kernel import HttpKernel
from service.logging_config import logger
from service.mcp_server import initialize
from service.routes import router

settings = with_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing Text2SQL service")
    logger.info(f"Pharia Kernel address: {settings.pharia_kernel_address}")
    logger.info(f"Database path: {settings.database_path}")
    logger.info(f"CORS enabled: {settings.enable_cors}")

    client = HttpKernel(str(settings.pharia_kernel_address))
    logger.info("HTTP Kernel client initialized")

    database = SQLiteDatabase(settings.database_path, auto_connect=True)
    logger.info("Database connection established")

    initialize(client, database)
    logger.info("Tool executor initialized")

    yield {"kernel": client, "database": database}

    logger.info("Application shutdown: Cleaning up resources")
    await client.shutdown()
    logger.debug("HTTP Kernel client shut down")
    database.disconnect()
    logger.debug("Database connection closed")
    logger.info("Application shutdown complete")


app = FastAPI(lifespan=lifespan)

###############################################################################
# WARNING: Do not modify this CORS configuration unless you fully understand    #
# the Pharia Applications Proxy implications.                                   #
#                                                                              #
# This configuration is strictly for local development/preview purposes.        #
# In production deployments, CORS is automatically handled by PhariaAI.     #
# Modifying these settings in production will cause header conflicts.           #
###############################################################################
if settings.enable_cors:
    app.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

app.include_router(router)


###############################################################################
# WARNING: Do not modify the UI serving configuration below unless you fully    #
# understand the implications.                                                  #
#                                                                              #
# The StaticFiles mount is required to serve the Application UI in          #
# PhariaAssistant.                                                            #
###############################################################################
app.mount("/ui", StaticFiles(directory="ui-artifacts"), name="ui")
app.mount("/data", StaticFiles(directory="src/data"), name="data")


def main():
    uvicorn.run("service.main:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()
