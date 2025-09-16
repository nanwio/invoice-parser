# Copyright 2024 Artificial Intelligence Labs, SL

from fastapi import APIRouter
from app.rest.parser import parser
from app.rest import health
from app.rest.verifactu import verifactu

router = APIRouter()
router.include_router(parser.router)
router.include_router(health.router)
router.include_router(verifactu.router, prefix="/verifactu", tags=["VERIFACTU"])
