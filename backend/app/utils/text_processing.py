"""
Text processing utilities for document parsing
"""
import re
from typing import List, Dict, Optional
from decimal import Decimal

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[^\x20-\x7E\n\t]', '', text)
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove excessive line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def extract_numbers(text: str) -> List[float]:
    """Extract numeric values from text"""
    # Pattern for numbers (including decimals and currency)
    number_pattern = r'[\$]?[\d,]+\.?\d*'
    matches = re.findall(number_pattern, text)
    
    numbers = []
    for match in matches:
        # Clean the number string
        cleaned = match.replace('$', '').replace(',', '')
        try:
            numbers.append(float(cleaned))
        except ValueError:
            continue
    
    return numbers

def extract_percentages(text: str) -> List[float]:
    """Extract percentage values from text"""
    # Pattern for percentages
    percentage_pattern = r'\d+\.?\d*\s*%'
    matches = re.findall(percentage_pattern, text)
    
    percentages = []
    for match in matches:
        # Extract just the number
        number_str = match.replace('%', '').strip()
        try:
            percentages.append(float(number_str))
        except ValueError:
            continue
    
    return percentages

def extract_dates(text: str) -> List[str]:
    """Extract date strings from text"""
    date_patterns = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',  # MM/DD/YYYY or MM-DD-YYYY
        r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',  # YYYY/MM/DD or YYYY-MM-DD
        r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}'
    ]
    
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates.extend(matches)
    
    return dates

def find_section_text(text: str, section_title: str, max_chars: int = 2000) -> Optional[str]:
    """Find text content for a specific section"""
    # Create flexible pattern for section titles
    title_pattern = re.escape(section_title).replace(r'\\ ', r'[\s\-_]*')
    pattern = fr'({title_pattern}.*?)(?=\n[A-Z][A-Z\s]+\.|$)'
    
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        section_text = match.group(1)
        return section_text[:max_chars] if len(section_text) > max_chars else section_text
    
    return None

def extract_partner_names(text: str) -> List[str]:
    """Extract potential partner/member names from text"""
    # Look for common patterns of partner listings
    patterns = [
        r'(?:Partner|Member|LP|GP):\s*([A-Z][a-zA-Z\s,\.]+?)(?=\n|\s{2,})',
        r'([A-Z][a-zA-Z\s]+),\s*(?:a|an)\s+(?:corporation|partnership|LLC|individual)',
        r'([A-Z][a-zA-Z\s]+)\s+\("?[A-Z][a-zA-Z\s]*"?\)'
    ]
    
    names = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Clean the name
            name = match.strip().rstrip(',').strip()
            if len(name) > 2 and len(name) < 100:  # Reasonable name length
                names.append(name)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_names = []
    for name in names:
        if name.lower() not in seen:
            seen.add(name.lower())
            unique_names.append(name)
    
    return unique_names

def extract_ownership_percentages(text: str) -> Dict[str, float]:
    """Extract ownership percentages associated with entity names"""
    # Pattern to find name followed by percentage
    pattern = r'([A-Z][a-zA-Z\s,\.]+?)[\s\-:]+(\d+\.?\d*)\s*%'
    matches = re.findall(pattern, text)
    
    ownership = {}
    for name, percentage in matches:
        name = name.strip().rstrip(',').strip()
        try:
            pct = float(percentage)
            if 0 <= pct <= 100:  # Valid percentage range
                ownership[name] = pct
        except ValueError:
            continue
    
    return ownership