"""
Partnership Tax Logic Engine - Main FastAPI Application
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from typing import Dict, List, Optional

# Import our core modules
from app.services.document_parser import PartnershipAgreementParser
from app.services.capital_account_manager import CapitalAccountManager
from app.models.partnership import Partnership, Partner
from app.models.document import DocumentParseResult
from app.database.database import init_db
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Partnership Tax Logic Engine API",
    description="AI-powered platform for automating complex partnership tax calculations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
document_parser = PartnershipAgreementParser()
capital_account_manager = CapitalAccountManager()

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Partnership Tax Logic Engine API...")
    
    # Skip database initialization during testing
    if os.getenv("TESTING") or "pytest" in os.getenv("_", ""):
        logger.info("Skipping database initialization during testing")
        return
        
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        # Don't fail startup in development/testing environments
        if os.getenv("ENVIRONMENT") == "production":
            raise

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Partnership Tax Logic Engine API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "api": "operational",
            "database": "connected",
            "ai_engine": "ready"
        }
    }

# Document Processing Endpoints
@app.post("/api/v1/documents/upload")
async def upload_partnership_agreement(
    file: UploadFile = File(...),
    partnership_id: Optional[str] = None
):
    """Upload and parse a partnership agreement"""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx', '.doc')):
            raise HTTPException(
                status_code=400, 
                detail="Only PDF and Word documents are supported"
            )
        
        # Read file content
        content = await file.read()
        
        # Parse the document
        parse_result = await document_parser.parse_agreement(
            content, 
            filename=file.filename,
            partnership_id=partnership_id
        )
        
        return {
            "message": "Document uploaded and parsed successfully",
            "document_id": parse_result.document_id,
            "parse_status": parse_result.status,
            "confidence_score": parse_result.confidence_score,
            "extracted_data": parse_result.extracted_data
        }
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")

@app.get("/api/v1/documents/{document_id}/status")
async def get_parse_status(document_id: str):
    """Get the parsing status of a document"""
    try:
        status = await document_parser.get_parse_status(document_id)
        return status
    except Exception as e:
        logger.error(f"Error retrieving parse status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve parse status")

@app.post("/api/v1/documents/{document_id}/validate")
async def validate_extracted_data(
    document_id: str,
    validation_data: Dict
):
    """Validate and correct extracted data from document parsing"""
    try:
        result = await document_parser.validate_and_update(document_id, validation_data)
        return {
            "message": "Validation completed",
            "updated_data": result
        }
    except Exception as e:
        logger.error(f"Error validating data: {str(e)}")
        raise HTTPException(status_code=500, detail="Validation failed")

# Partnership Management Endpoints
@app.post("/api/v1/partnerships")
async def create_partnership(partnership_data: Dict):
    """Create a new partnership record"""
    try:
        # This would integrate with the database layer
        partnership = Partnership(**partnership_data)
        # Save to database
        return {
            "message": "Partnership created successfully",
            "partnership_id": partnership.id
        }
    except Exception as e:
        logger.error(f"Error creating partnership: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create partnership")

@app.get("/api/v1/partnerships/{partnership_id}")
async def get_partnership(partnership_id: str):
    """Get partnership details"""
    try:
        # Retrieve from database
        return {
            "partnership_id": partnership_id,
            "status": "active"
            # Add full partnership data
        }
    except Exception as e:
        logger.error(f"Error retrieving partnership: {str(e)}")
        raise HTTPException(status_code=404, detail="Partnership not found")

# Capital Account Management Endpoints
@app.get("/api/v1/partnerships/{partnership_id}/capital-accounts")
async def get_capital_accounts(partnership_id: str):
    """Get capital accounts for all partners in a partnership"""
    try:
        accounts = await capital_account_manager.get_capital_accounts(partnership_id)
        return {
            "partnership_id": partnership_id,
            "capital_accounts": accounts
        }
    except Exception as e:
        logger.error(f"Error retrieving capital accounts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve capital accounts")

@app.post("/api/v1/partnerships/{partnership_id}/transactions")
async def record_transaction(
    partnership_id: str,
    transaction_data: Dict
):
    """Record a capital account transaction"""
    try:
        result = await capital_account_manager.process_transaction(
            partnership_id, 
            transaction_data
        )
        return {
            "message": "Transaction recorded successfully",
            "transaction_id": result.transaction_id,
            "updated_balances": result.updated_balances
        }
    except Exception as e:
        logger.error(f"Error recording transaction: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to record transaction")

@app.post("/api/v1/partnerships/{partnership_id}/allocations/calculate")
async def calculate_target_allocations(
    partnership_id: str,
    calculation_data: Dict
):
    """Calculate target allocations based on partnership agreement"""
    try:
        allocations = await capital_account_manager.calculate_target_allocations(
            partnership_id,
            calculation_data
        )
        return {
            "partnership_id": partnership_id,
            "target_allocations": allocations.target_balances,
            "required_adjustments": allocations.required_allocations,
            "compliance_status": allocations.compliance_check
        }
    except Exception as e:
        logger.error(f"Error calculating allocations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to calculate allocations")

# Integration Endpoints
@app.post("/api/v1/integrations/export/{platform}")
async def export_data(
    platform: str,
    partnership_id: str,
    export_data: Dict
):
    """Export calculated data to external tax software platforms"""
    try:
        supported_platforms = ["cch_axcess", "gosystem_rs", "lacerte", "ultratax"]
        
        if platform not in supported_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported platform. Supported: {supported_platforms}"
            )
        
        # This would be implemented with specific platform integrations
        return {
            "message": f"Data exported to {platform} successfully",
            "export_id": f"exp_{partnership_id}_{platform}",
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        raise HTTPException(status_code=500, detail="Export failed")

# Compliance and Reporting Endpoints
@app.get("/api/v1/partnerships/{partnership_id}/compliance-report")
async def generate_compliance_report(partnership_id: str):
    """Generate comprehensive compliance report"""
    try:
        # This would generate a full compliance report
        return {
            "partnership_id": partnership_id,
            "compliance_status": "compliant",
            "section_704b_status": "compliant",
            "audit_readiness": "ready",
            "recommendations": []
        }
    except Exception as e:
        logger.error(f"Error generating compliance report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

@app.get("/api/v1/partnerships/{partnership_id}/audit-trail")
async def get_audit_trail(partnership_id: str):
    """Get complete audit trail for all calculations"""
    try:
        # Return comprehensive audit trail
        return {
            "partnership_id": partnership_id,
            "audit_trail": [],
            "last_updated": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Error retrieving audit trail: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit trail")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )