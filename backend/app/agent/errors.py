from typing import Any, Dict


class AgentError(ValueError):
    """A business exception the voice agent must explain or resolve with the user.

    Subclasses ValueError so existing service callers that catch ValueError keep working.
    `code` is a stable machine-readable identifier the LLM is instructed to act on.
    """

    # Codes the system prompt tells Gemini how to handle
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    MULTIPLE_MATCHES = "MULTIPLE_MATCHES"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    AMBIGUOUS_PRODUCT = "AMBIGUOUS_PRODUCT"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    INVALID_AMOUNT = "INVALID_AMOUNT"
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    ACTION_NOT_FOUND = "ACTION_NOT_FOUND"
    NOTHING_TO_UNDO = "NOTHING_TO_UNDO"
    UNDO_NOT_ALLOWED = "UNDO_NOT_ALLOWED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {"success": False, "error_code": self.code, "error": self.message, **self.details}
