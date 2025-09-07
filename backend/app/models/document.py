"""
Document-related models
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class DocumentParseResult(BaseModel):
    """Result of document parsing operation"""
    document_id: str
    partnership_id: Optional[str] = None
    filename: str
    status: str  # pending, completed, failed, requires_review
    confidence_score: float
    extracted_data: Dict[str, Any]
    raw_text: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

class PartnershipAgreement(BaseModel):
    """Parsed partnership agreement data"""
    partnership_name: str
    formation_date: Optional[datetime] = None
    jurisdiction: Optional[str] = None
    partners: list = []
    capital_structure: Dict[str, Any] = {}
    distribution_waterfall: list = []
    management_provisions: Dict[str, Any] = {}
    tax_provisions: Dict[str, Any] = {}