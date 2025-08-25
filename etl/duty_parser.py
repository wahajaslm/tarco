# WORKFLOW: Duty parser for parsing various duty formats in trade compliance data.
# Used by: ETL pipeline, measure transformation, duty component extraction
# Functions:
# 1. parse_duty_components() - Parse duty string into structured components
# 2. parse_ad_valorem() - Parse percentage-based duties
# 3. parse_specific() - Parse specific duties (EUR/100kg, EUR/unit)
# 4. parse_compound() - Parse compound duties (%, +, min/max)
# 5. validate_duty_format() - Validate duty string format
#
# Parsing flow: Duty string -> Format detection -> Component extraction -> Structured data
# Supports: ad valorem (%), specific (EUR/100kg, EUR/unit), compound (%, +, min/max)
# This ensures all duty data is properly structured for the API responses.

"""
Duty parser for parsing various duty formats in trade compliance data.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def parse_ad_valorem(duty_str: str) -> Dict[str, Any]:
    """
    Parse ad valorem duty (percentage-based).
    
    Args:
        duty_str: Duty string (e.g., "12.5%", "0%")
        
    Returns:
        Dictionary with duty component structure
    """
    try:
        # Extract percentage value
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', duty_str)
        if not match:
            raise ValueError(f"Invalid ad valorem format: {duty_str}")
        
        value = float(match.group(1))
        
        return {
            "type": "ad_valorem",
            "value": value,
            "unit": "percent"
        }
        
    except Exception as e:
        logger.error(f"Failed to parse ad valorem duty '{duty_str}': {e}")
        raise


def parse_specific(duty_str: str) -> Dict[str, Any]:
    """
    Parse specific duty (EUR/100kg, EUR/unit, etc.).
    
    Args:
        duty_str: Duty string (e.g., "EUR 2.50/100kg", "EUR 5.00/unit")
        
    Returns:
        Dictionary with duty component structure
    """
    try:
        # Extract currency, value, and unit
        match = re.search(r'([A-Z]{3})\s*(\d+(?:\.\d+)?)\s*/\s*(\d+)?\s*(\w+)', duty_str)
        if not match:
            raise ValueError(f"Invalid specific duty format: {duty_str}")
        
        currency = match.group(1)
        value = float(match.group(2))
        quantity = int(match.group(3)) if match.group(3) else 1
        unit = match.group(4)
        
        # Determine unit type
        if unit.lower() in ['kg', '100kg']:
            unit_type = "eur/100kg"
        elif unit.lower() in ['unit', 'piece', 'item']:
            unit_type = "eur/unit"
        else:
            unit_type = f"eur/{unit.lower()}"
        
        return {
            "type": "specific",
            "value": value,
            "unit": unit_type,
            "currency": currency,
            "quantity": quantity
        }
        
    except Exception as e:
        logger.error(f"Failed to parse specific duty '{duty_str}': {e}")
        raise


def parse_compound(duty_str: str) -> Dict[str, Any]:
    """
    Parse compound duty (combination of ad valorem and specific).
    
    Args:
        duty_str: Duty string (e.g., "12.5% + EUR 2.50/100kg", "min EUR 5.00/unit")
        
    Returns:
        Dictionary with compound duty structure
    """
    try:
        components = []
        
        # Check for min/max patterns
        min_match = re.search(r'min\s+([A-Z]{3})\s*(\d+(?:\.\d+)?)\s*/\s*(\w+)', duty_str, re.IGNORECASE)
        max_match = re.search(r'max\s+([A-Z]{3})\s*(\d+(?:\.\d+)?)\s*/\s*(\w+)', duty_str, re.IGNORECASE)
        
        if min_match or max_match:
            # Min/max specific duty
            if min_match:
                currency = min_match.group(1)
                value = float(min_match.group(2))
                unit = min_match.group(3)
                min_value = value
                max_value = None
            else:
                currency = max_match.group(1)
                value = float(max_match.group(2))
                unit = max_match.group(3)
                min_value = None
                max_value = value
            
            unit_type = "eur/100kg" if unit.lower() in ['kg', '100kg'] else "eur/unit"
            
            return {
                "type": "compound",
                "components": [
                    {
                        "type": "specific",
                        "value": value,
                        "unit": unit_type,
                        "currency": currency,
                        "min_value": min_value,
                        "max_value": max_value
                    }
                ],
                "unit": "mixed"
            }
        
        # Check for percentage + specific pattern
        parts = duty_str.split('+')
        if len(parts) == 2:
            # Parse ad valorem part
            ad_valorem_part = parts[0].strip()
            if '%' in ad_valorem_part:
                ad_valorem = parse_ad_valorem(ad_valorem_part)
                components.append(ad_valorem)
            
            # Parse specific part
            specific_part = parts[1].strip()
            if any(currency in specific_part for currency in ['EUR', 'USD', 'GBP']):
                specific = parse_specific(specific_part)
                components.append(specific)
            
            return {
                "type": "compound",
                "components": components,
                "unit": "mixed"
            }
        
        # If no compound pattern found, try as single duty
        if '%' in duty_str:
            return parse_ad_valorem(duty_str)
        elif any(currency in duty_str for currency in ['EUR', 'USD', 'GBP']):
            return parse_specific(duty_str)
        else:
            raise ValueError(f"Unrecognized compound duty format: {duty_str}")
        
    except Exception as e:
        logger.error(f"Failed to parse compound duty '{duty_str}': {e}")
        raise


def validate_duty_format(duty_str: str) -> bool:
    """
    Validate duty string format.
    
    Args:
        duty_str: Duty string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check for empty or None
        if not duty_str or duty_str.strip() == '':
            return False
        
        # Check for common patterns
        patterns = [
            r'\d+(?:\.\d+)?\s*%',  # Ad valorem
            r'[A-Z]{3}\s*\d+(?:\.\d+)?\s*/\s*\d*\s*\w+',  # Specific
            r'(?:min|max)\s+[A-Z]{3}\s*\d+(?:\.\d+)?\s*/\s*\w+',  # Min/max
            r'\d+(?:\.\d+)?\s*%\s*\+\s*[A-Z]{3}\s*\d+(?:\.\d+)?\s*/\s*\w+'  # Compound
        ]
        
        for pattern in patterns:
            if re.search(pattern, duty_str, re.IGNORECASE):
                return True
        
        return False
        
    except Exception:
        return False


def parse_duty_components(duty_str: str) -> List[Dict[str, Any]]:
    """
    Parse duty string into structured components.
    
    Args:
        duty_str: Duty string to parse
        
    Returns:
        List of duty component dictionaries
    """
    try:
        if not duty_str or duty_str.strip() == '':
            return []
        
        duty_str = duty_str.strip()
        
        # Validate format
        if not validate_duty_format(duty_str):
            logger.warning(f"Invalid duty format: {duty_str}")
            return []
        
        # Determine duty type and parse accordingly
        if '%' in duty_str and ('+' in duty_str or re.search(r'(?:min|max)', duty_str, re.IGNORECASE)):
            # Compound duty
            compound = parse_compound(duty_str)
            return [compound] if compound else []
        elif '%' in duty_str:
            # Ad valorem duty
            ad_valorem = parse_ad_valorem(duty_str)
            return [ad_valorem] if ad_valorem else []
        elif any(currency in duty_str for currency in ['EUR', 'USD', 'GBP']):
            # Specific duty
            specific = parse_specific(duty_str)
            return [specific] if specific else []
        else:
            logger.warning(f"Unrecognized duty format: {duty_str}")
            return []
        
    except Exception as e:
        logger.error(f"Failed to parse duty components '{duty_str}': {e}")
        return []


def format_duty_for_display(duty_components: List[Dict[str, Any]]) -> str:
    """
    Format duty components for human-readable display.
    
    Args:
        duty_components: List of duty component dictionaries
        
    Returns:
        Formatted duty string
    """
    try:
        if not duty_components:
            return "0%"
        
        formatted_parts = []
        
        for component in duty_components:
            if component.get("type") == "ad_valorem":
                formatted_parts.append(f"{component['value']}%")
            elif component.get("type") == "specific":
                currency = component.get("currency", "EUR")
                value = component["value"]
                unit = component["unit"]
                if unit == "eur/100kg":
                    formatted_parts.append(f"{currency} {value}/100kg")
                elif unit == "eur/unit":
                    formatted_parts.append(f"{currency} {value}/unit")
                else:
                    formatted_parts.append(f"{currency} {value}/{unit}")
            elif component.get("type") == "compound":
                # Handle compound components
                for sub_component in component.get("components", []):
                    if sub_component.get("type") == "ad_valorem":
                        formatted_parts.append(f"{sub_component['value']}%")
                    elif sub_component.get("type") == "specific":
                        currency = sub_component.get("currency", "EUR")
                        value = sub_component["value"]
                        unit = sub_component["unit"]
                        if unit == "eur/100kg":
                            formatted_parts.append(f"{currency} {value}/100kg")
                        elif unit == "eur/unit":
                            formatted_parts.append(f"{currency} {value}/unit")
                        else:
                            formatted_parts.append(f"{currency} {value}/{unit}")
        
        return " + ".join(formatted_parts)
        
    except Exception as e:
        logger.error(f"Failed to format duty for display: {e}")
        return "Unknown"


if __name__ == "__main__":
    # Test duty parsing
    test_duties = [
        "12.5%",
        "EUR 2.50/100kg",
        "EUR 5.00/unit",
        "12.5% + EUR 2.50/100kg",
        "min EUR 5.00/unit",
        "max EUR 10.00/100kg"
    ]
    
    for duty in test_duties:
        print(f"Parsing: {duty}")
        components = parse_duty_components(duty)
        print(f"Components: {components}")
        formatted = format_duty_for_display(components)
        print(f"Formatted: {formatted}")
        print()
