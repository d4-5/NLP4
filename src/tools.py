import re
from typing import Any, Dict
try:
    from src.ie_rules import extract_dates, extract_amounts, extract_doc_ids
except ImportError:
    from ie_rules import extract_dates, extract_amounts, extract_doc_ids

def classify_issue(text: str) -> Dict[str, Any]:
    """
    Classifies the support issue into one of: Payment, Technical, General.
    """
    text_lower = text.lower()
    
    payment_keywords = ["платіж", "гроші", "картк", "оплат", "чек", "рахунок", "вартість", "payment", "money", "card", "pay"]
    tech_keywords = ["помилка", "баг", "не працює", "логін", "пароль", "сайт", "додаток", "error", "bug", "broken", "login", "app"]
    
    payment_score = sum(1 for word in payment_keywords if word in text_lower)
    tech_score = sum(1 for word in tech_keywords if word in text_lower)
    
    if payment_score > tech_score and payment_score > 0:
        return {"category": "Payment", "confidence": min(1.0, 0.5 + 0.1 * payment_score)}
    elif tech_score > payment_score and tech_score > 0:
        return {"category": "Technical", "confidence": min(1.0, 0.5 + 0.1 * tech_score)}
    else:
        return {"category": "General", "confidence": 0.5}

def extract_support_entities(text: str) -> Dict[str, Any]:
    """
    Extracts relevant entities for support tickets (Order ID, Amount, Date).
    """
    dates = extract_dates(text)
    amounts = extract_amounts(text)
    doc_ids = extract_doc_ids(text)
    
    return {
        "dates": [d["value"] for d in dates],
        "amounts": [{"value": a["value"], "currency": a["currency"]} for a in amounts],
        "doc_ids": [d["value"] for d in doc_ids if d["type"] in ["CONTRACT_ID", "GENERIC_DOC_ID", "ORDER_ID"]],
        "case_ids": [d["value"] for d in doc_ids if d["type"] == "CASE_ID"]
    }

def validate_support_fields(category: str, entities: Any) -> Dict[str, Any]:
    """
    Validates if the ticket contains all necessary information for the category.
    """
    if isinstance(entities, str):
        try:
            if entities.startswith("{") and not entities.endswith("}"):
                entities += "}"
            entities = json.loads(entities.replace("'", '"'))
        except:
            return {"is_valid": False, "missing_fields": ["All (failed to parse entities)"], "message": "Critical: Could not parse entities data."}
    
    if not isinstance(entities, dict):
        return {"is_valid": False, "missing_fields": ["All (entities must be dict)"], "message": "Critical: Entities must be a dictionary."}

    missing = []
    if category == "Payment":
        if not entities.get("amounts"):
            missing.append("Amount")
        if not entities.get("dates"):
            missing.append("Date of payment")
    elif category == "Technical":
        if not entities.get("doc_ids") and not entities.get("case_ids"):
            missing.append("Reference ID (Order/Case)")
            
    is_valid = len(missing) == 0
    return {
        "is_valid": is_valid,
        "missing_fields": missing,
        "message": "Information is complete" if is_valid else f"Missing information: {', '.join(missing)}"
    }
