"""
Test suite for Partnership Agreement Parser
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

from app.services.document_parser import PartnershipAgreementParser
from app.models.document import DocumentParseResult

class TestPartnershipAgreementParser:
    """Test cases for the partnership agreement parser"""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance for testing"""
        return PartnershipAgreementParser()
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content for testing"""
        return b"Sample PDF content for testing"
    
    @pytest.fixture
    def sample_agreement_text(self):
        """Sample partnership agreement text"""
        return """
        PARTNERSHIP AGREEMENT
        
        ABC Real Estate Partners, LP
        
        PARTNERS:
        General Partner: ABC GP, LLC - 2%
        Limited Partner: Investment Fund A - 60%
        Limited Partner: Investment Fund B - 38%
        
        CAPITAL CONTRIBUTIONS:
        Total commitment: $10,000,000
        
        DISTRIBUTION WATERFALL:
        1. Return of capital contributions
        2. 8% preferred return to Limited Partners
        3. 20% catch-up to General Partner
        4. Remaining 80/20 split
        """
    
    @pytest.mark.asyncio
    async def test_parse_agreement_success(self, parser, sample_pdf_content):
        """Test successful agreement parsing"""
        with patch.object(parser, '_extract_text') as mock_extract_text, \
             patch.object(parser, '_extract_partnership_data') as mock_extract_data:
            
            # Mock text extraction
            mock_extract_text.return_value = "Sample partnership agreement text"
            
            # Mock data extraction
            mock_extraction_results = [
                Mock(
                    confidence=0.9,
                    data={"partnership_name": "ABC Real Estate Partners, LP"},
                    source_text="Sample text"
                )
            ]
            mock_extract_data.return_value = mock_extraction_results
            
            # Execute parsing
            result = await parser.parse_agreement(
                content=sample_pdf_content,
                filename="test_agreement.pdf",
                partnership_id="test-id"
            )
            
            # Assertions
            assert isinstance(result, DocumentParseResult)
            assert result.filename == "test_agreement.pdf"
            assert result.partnership_id == "test-id"
            assert result.status in ["completed", "requires_review"]
            assert result.confidence_score > 0
            assert result.extracted_data is not None
    
    @pytest.mark.asyncio
    async def test_parse_agreement_failure(self, parser, sample_pdf_content):
        """Test parsing failure handling"""
        with patch.object(parser, '_extract_text') as mock_extract_text:
            # Mock extraction failure
            mock_extract_text.side_effect = Exception("PDF extraction failed")
            
            # Execute parsing
            result = await parser.parse_agreement(
                content=sample_pdf_content,
                filename="test_agreement.pdf"
            )
            
            # Assertions
            assert result.status == "failed"
            assert result.confidence_score == 0.0
            assert result.error_message is not None
            assert "PDF extraction failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_extract_pdf_text(self, parser):
        """Test PDF text extraction"""
        # This would require a real PDF file for proper testing
        # For now, test that the method handles exceptions
        with pytest.raises(Exception):
            await parser._extract_pdf_text(b"invalid pdf content")
    
    def test_split_document(self, parser, sample_agreement_text):
        """Test document splitting into chunks"""
        chunks = parser._split_document(sample_agreement_text)
        
        assert len(chunks) > 0
        assert all(hasattr(chunk, 'page_content') for chunk in chunks)
        assert all(hasattr(chunk, 'metadata') for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_analyze_chunk_with_partnership_data(self, parser):
        """Test chunk analysis with partnership information"""
        from langchain.schema import Document
        
        chunk = Document(
            page_content="ABC Real Estate Partners, LP with General Partner owning 2%",
            metadata={"chunk_id": 0}
        )
        
        with patch.object(parser.openai_client.chat.completions, 'create') as mock_openai:
            # Mock OpenAI response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = """
            {
                "partnership_name": {"value": "ABC Real Estate Partners, LP", "confidence": 0.95},
                "general_partner": {"value": "General Partner", "confidence": 0.85}
            }
            """
            mock_openai.return_value = mock_response
            
            result = await parser._analyze_chunk(chunk)
            
            assert result is not None
            assert result.confidence > 0
            assert "partnership_name" in result.data
    
    @pytest.mark.asyncio
    async def test_analyze_chunk_no_data(self, parser):
        """Test chunk analysis with no relevant data"""
        from langchain.schema import Document
        
        chunk = Document(
            page_content="This is irrelevant text with no partnership information",
            metadata={"chunk_id": 0}
        )
        
        with patch.object(parser.openai_client.chat.completions, 'create') as mock_openai:
            # Mock OpenAI response with null
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "null"
            mock_openai.return_value = mock_response
            
            result = await parser._analyze_chunk(chunk)
            
            assert result is None
    
    def test_consolidate_extractions(self, parser):
        """Test consolidation of extraction results"""
        from app.services.document_parser import ExtractionResult
        
        results = [
            ExtractionResult(
                confidence=0.9,
                data={
                    "partnership_info": {"name": "ABC Partners"},
                    "partners": [{"name": "Partner A", "ownership": 60}]
                },
                source_text="Sample text 1"
            ),
            ExtractionResult(
                confidence=0.8,
                data={
                    "partnership_info": {"jurisdiction": "Delaware"},
                    "partners": [{"name": "Partner B", "ownership": 40}]
                },
                source_text="Sample text 2"
            )
        ]
        
        consolidated = parser._consolidate_extractions(results)
        
        assert "partnership_info" in consolidated
        assert "partners" in consolidated
        assert len(consolidated["partners"]) == 2
        assert consolidated["metadata"]["total_chunks_analyzed"] == 2
    
    def test_validate_consolidated_data(self, parser):
        """Test validation of consolidated data"""
        data = {
            "partners": [
                {"name": "Partner A", "ownership_percentage": 60},
                {"name": "Partner B", "ownership_percentage": 40},
                {"name": "Partner A", "ownership_percentage": 60}  # Duplicate
            ],
            "metadata": {}
        }
        
        validated_data = parser._validate_consolidated_data(data)
        
        # Should remove duplicates
        assert len(validated_data["partners"]) == 2
        assert validated_data["metadata"]["total_ownership_percentage"] == 100
        assert validated_data["metadata"]["ownership_totals_valid"] is True
    
    def test_calculate_confidence_empty_results(self, parser):
        """Test confidence calculation with empty results"""
        confidence = parser._calculate_confidence([])
        assert confidence == 0.0
    
    def test_calculate_confidence_with_results(self, parser):
        """Test confidence calculation with results"""
        from app.services.document_parser import ExtractionResult
        
        results = [
            ExtractionResult(confidence=0.9, data={"test": "data"}, source_text="text1"),
            ExtractionResult(confidence=0.8, data={"test": "data"}, source_text="text2")
        ]
        
        confidence = parser._calculate_confidence(results)
        
        assert 0 <= confidence <= 1
        assert confidence > 0

# Integration tests
class TestPartnershipAgreementParserIntegration:
    """Integration tests for the parser with real-like data"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_parsing_simulation(self):
        """Test end-to-end parsing with simulated data"""
        parser = PartnershipAgreementParser()
        
        # Create mock agreement content
        agreement_content = """
        LIMITED PARTNERSHIP AGREEMENT
        OF
        REAL ESTATE INVESTMENT FUND I, L.P.
        
        ARTICLE I - FORMATION
        The Limited Partnership is formed under Delaware law.
        
        ARTICLE II - PARTNERS
        General Partner: RE Fund GP, LLC (1.0%)
        Limited Partners:
        - Institutional Investor A (45.0%)
        - Institutional Investor B (35.0%)
        - High Net Worth Individual C (19.0%)
        
        ARTICLE III - CAPITAL CONTRIBUTIONS
        Total Capital Commitments: $50,000,000
        
        ARTICLE IV - DISTRIBUTIONS
        Waterfall:
        1. Return of Capital Contributions
        2. 8% Preferred Return to Limited Partners
        3. 20% Catch-up to General Partner
        4. Thereafter 80% Limited Partners, 20% General Partner
        """
        
        with patch.object(parser, '_extract_text') as mock_extract_text, \
             patch.object(parser.openai_client.chat.completions, 'create') as mock_openai:
            
            mock_extract_text.return_value = agreement_content
            
            # Mock realistic OpenAI responses
            mock_responses = [
                {
                    "partnership_info": {
                        "name": {"value": "Real Estate Investment Fund I, L.P.", "confidence": 0.95},
                        "jurisdiction": {"value": "Delaware", "confidence": 0.90}
                    }
                },
                {
                    "partners": [
                        {"name": "RE Fund GP, LLC", "type": "general", "ownership_percentage": 1.0, "confidence": 0.95},
                        {"name": "Institutional Investor A", "type": "limited", "ownership_percentage": 45.0, "confidence": 0.90}
                    ]
                },
                {
                    "distributions": {
                        "waterfall_type": "standard_pe",
                        "preferred_return": 8.0,
                        "catch_up": 20.0,
                        "confidence": 0.85
                    }
                }
            ]
            
            # Mock OpenAI to return different responses for different chunks
            call_count = 0
            def mock_openai_response(*args, **kwargs):
                nonlocal call_count
                response = Mock()
                response.choices = [Mock()]
                if call_count < len(mock_responses):
                    response.choices[0].message.content = str(mock_responses[call_count]).replace("'", '"')
                else:
                    response.choices[0].message.content = "null"
                call_count += 1
                return response
            
            mock_openai.side_effect = mock_openai_response
            
            # Execute parsing
            result = await parser.parse_agreement(
                content=b"mock_pdf_content",
                filename="real_estate_fund.pdf",
                partnership_id="fund-001"
            )
            
            # Verify results
            assert result.status in ["completed", "requires_review"]
            assert result.confidence_score > 0.5
            assert result.partnership_id == "fund-001"
            assert result.filename == "real_estate_fund.pdf"
            
            # Check that data was extracted
            assert result.extracted_data is not None
            assert "partnership_info" in result.extracted_data or "partners" in result.extracted_data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])