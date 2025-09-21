# Copyright 2024 Artificial Intelligence Labs, SL

from fastapi import APIRouter
from app.rest.parser import parser
from app.rest import health
# TODO: Enable VERIFACTU when core functionality is stable
# from app.rest.verifactu import verifactu

router = APIRouter()
router.include_router(parser.router)
router.include_router(health.router)
# TODO: Enable VERIFACTU routes when ready for production
# router.include_router(verifactu.router, prefix="/verifactu", tags=["VERIFACTU"])
