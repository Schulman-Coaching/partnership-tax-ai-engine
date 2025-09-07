"""
Partnership Data Models
SQLAlchemy models for partnership entities, partners, and capital accounts
"""
from sqlalchemy import Column, String, Integer, Decimal, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal as PyDecimal
import uuid

Base = declarative_base()

class Partnership(Base):
    """Partnership/LLC entity model"""
    __tablename__ = "partnerships"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    ein = Column(String(10), unique=True, nullable=True)  # Employer Identification Number
    entity_type = Column(String(50), nullable=False, default="partnership")  # partnership, llc, etc.
    formation_date = Column(DateTime, nullable=True)
    tax_year_end = Column(String(10), default="12-31")  # MM-DD format
    jurisdiction = Column(String(100), nullable=True)  # State/country of formation
    
    # Agreement tracking
    current_agreement_id = Column(String(36), nullable=True)
    agreement_effective_date = Column(DateTime, nullable=True)
    
    # Tax settings
    tax_method = Column(String(20), default="cash")  # cash, accrual
    section_754_election = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String(36), nullable=True)
    
    # Relationships
    partners = relationship("Partner", back_populates="partnership", cascade="all, delete-orphan")
    capital_accounts = relationship("CapitalAccount", back_populates="partnership")
    documents = relationship("Document", back_populates="partnership")
    transactions = relationship("Transaction", back_populates="partnership")

class Partner(Base):
    """Partner/Member model"""
    __tablename__ = "partners"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    partnership_id = Column(String(36), ForeignKey("partnerships.id"), nullable=False)
    
    # Partner identification
    name = Column(String(255), nullable=False)
    partner_type = Column(String(20), nullable=False)  # general, limited, managing_member, etc.
    entity_type = Column(String(20), default="individual")  # individual, corporation, partnership, etc.
    tax_id = Column(String(20), nullable=True)  # SSN, EIN, etc.
    
    # Ownership and economic terms
    ownership_percentage = Column(Decimal(5, 4), nullable=False)  # 0.0000 to 1.0000
    voting_percentage = Column(Decimal(5, 4), nullable=True)
    profit_sharing_percentage = Column(Decimal(5, 4), nullable=True)
    loss_sharing_percentage = Column(Decimal(5, 4), nullable=True)
    
    # Capital and contribution terms
    capital_commitment = Column(Decimal(15, 2), nullable=True)
    capital_contributed_to_date = Column(Decimal(15, 2), default=0)
    
    # Special rights and provisions
    receives_management_fee = Column(Boolean, default=False)
    receives_promote = Column(Boolean, default=False)
    promote_percentage = Column(Decimal(5, 4), nullable=True)
    preferred_return_rate = Column(Decimal(5, 4), nullable=True)
    
    # Status tracking
    admission_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")  # active, withdrawn, deceased, etc.
    
    # Contact information
    address = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    partnership = relationship("Partnership", back_populates="partners")
    capital_accounts = relationship("CapitalAccount", back_populates="partner")
    transactions = relationship("Transaction", back_populates="partner")

class CapitalAccount(Base):
    """Capital Account tracking model"""
    __tablename__ = "capital_accounts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    partnership_id = Column(String(36), ForeignKey("partnerships.id"), nullable=False)
    partner_id = Column(String(36), ForeignKey("partners.id"), nullable=False)
    
    # Period information
    period_end_date = Column(DateTime, nullable=False)
    period_type = Column(String(20), default="year_end")  # year_end, quarterly, monthly
    
    # Capital account balances (Section 704(b) book method)
    beginning_balance = Column(Decimal(15, 2), default=0)
    contributions = Column(Decimal(15, 2), default=0)
    distributions = Column(Decimal(15, 2), default=0)
    income_allocations = Column(Decimal(15, 2), default=0)
    loss_allocations = Column(Decimal(15, 2), default=0)
    other_increases = Column(Decimal(15, 2), default=0)
    other_decreases = Column(Decimal(15, 2), default=0)
    ending_balance = Column(Decimal(15, 2), default=0)
    
    # Alternative capital account methods
    tax_basis_balance = Column(Decimal(15, 2), nullable=True)
    gaap_balance = Column(Decimal(15, 2), nullable=True)
    
    # Special tracking
    preferred_return_accrued = Column(Decimal(15, 2), default=0)
    promote_earned = Column(Decimal(15, 2), default=0)
    
    # Deficit tracking for DRO/QIO compliance
    deficit_restoration_obligation = Column(Decimal(15, 2), nullable=True)
    has_deficit = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    calculation_method = Column(String(50), default="target_allocation")
    calculation_notes = Column(Text, nullable=True)
    
    # Relationships
    partnership = relationship("Partnership", back_populates="capital_accounts")
    partner = relationship("Partner", back_populates="capital_accounts")

class Transaction(Base):
    """Capital account transaction model"""
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    partnership_id = Column(String(36), ForeignKey("partnerships.id"), nullable=False)
    partner_id = Column(String(36), ForeignKey("partners.id"), nullable=True)  # Null for partnership-level
    
    # Transaction details
    transaction_date = Column(DateTime, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # contribution, distribution, allocation, etc.
    amount = Column(Decimal(15, 2), nullable=False)
    description = Column(Text, nullable=True)
    
    # Classification
    account_category = Column(String(50), nullable=True)  # capital, income, expense, etc.
    allocation_type = Column(String(50), nullable=True)  # ordinary, capital_gain, section_1231, etc.
    
    # Source documentation
    source_document = Column(String(255), nullable=True)
    journal_entry_reference = Column(String(100), nullable=True)
    
    # Tax attributes
    tax_year = Column(Integer, nullable=False)
    book_tax_difference = Column(Decimal(15, 2), default=0)
    
    # Approval and processing
    status = Column(String(20), default="pending")  # pending, approved, posted, reversed
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String(36), nullable=True)
    
    # Relationships
    partnership = relationship("Partnership", back_populates="transactions")
    partner = relationship("Partner", back_populates="transactions")

class Document(Base):
    """Document storage and parsing results"""
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    partnership_id = Column(String(36), ForeignKey("partnerships.id"), nullable=True)
    
    # Document metadata
    filename = Column(String(500), nullable=False)
    document_type = Column(String(100), nullable=False)  # partnership_agreement, amendment, etc.
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Storage information
    file_path = Column(String(1000), nullable=True)
    storage_provider = Column(String(50), default="local")  # local, s3, azure, etc.
    
    # Parsing results
    parse_status = Column(String(20), default="pending")  # pending, completed, failed, requires_review
    confidence_score = Column(Decimal(3, 2), nullable=True)  # 0.00 to 1.00
    parsed_data = Column(JSON, nullable=True)
    raw_text_preview = Column(Text, nullable=True)  # First few thousand chars for preview
    
    # Processing timestamps
    uploaded_at = Column(DateTime, default=func.now())
    parsed_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Validation and review
    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    validation_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String(36), nullable=True)
    
    # Relationships
    partnership = relationship("Partnership", back_populates="documents")

class AllocationRun(Base):
    """Track allocation calculation runs"""
    __tablename__ = "allocation_runs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    partnership_id = Column(String(36), ForeignKey("partnerships.id"), nullable=False)
    
    # Run metadata
    run_name = Column(String(255), nullable=False)
    run_type = Column(String(50), default="target_allocation")  # target_allocation, special_allocation, etc.
    tax_year = Column(Integer, nullable=False)
    period_end_date = Column(DateTime, nullable=False)
    
    # Input data
    net_income = Column(Decimal(15, 2), nullable=False)
    input_data = Column(JSON, nullable=True)  # Store calculation inputs
    
    # Results
    status = Column(String(20), default="running")  # running, completed, failed
    results = Column(JSON, nullable=True)  # Store calculation results
    compliance_check = Column(JSON, nullable=True)
    
    # Execution details
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    execution_time_seconds = Column(Decimal(10, 3), nullable=True)
    
    # Metadata
    created_by = Column(String(36), nullable=True)
    notes = Column(Text, nullable=True)

# Pydantic models for API serialization
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class PartnershipBase(BaseModel):
    name: str
    ein: Optional[str] = None
    entity_type: str = "partnership"
    formation_date: Optional[datetime] = None
    tax_year_end: str = "12-31"
    jurisdiction: Optional[str] = None
    tax_method: str = "cash"
    section_754_election: bool = False

class PartnershipCreate(PartnershipBase):
    pass

class PartnershipResponse(PartnershipBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PartnerBase(BaseModel):
    name: str
    partner_type: str
    entity_type: str = "individual"
    ownership_percentage: PyDecimal
    capital_commitment: Optional[PyDecimal] = None
    receives_management_fee: bool = False
    receives_promote: bool = False

class PartnerCreate(PartnerBase):
    partnership_id: str

class PartnerResponse(PartnerBase):
    id: str
    partnership_id: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class DocumentParseResult(BaseModel):
    """Result of document parsing operation"""
    document_id: str
    partnership_id: Optional[str] = None
    filename: str
    status: str
    confidence_score: float
    extracted_data: Dict[str, Any]
    raw_text: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

class AllocationResult(BaseModel):
    """Result of allocation calculation"""
    target_balances: Dict[str, PyDecimal]
    required_allocations: Dict[str, PyDecimal]
    compliance_check: Dict[str, bool]
    calculation_method: str
    waterfall_analysis: Dict[str, Any]