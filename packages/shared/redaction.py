"""
Secret Redaction Middleware

Redacts sensitive information from tool outputs before JSONL persistence.
Prevents accidental storage of API keys, passwords, tokens, and other secrets.

Usage:
    from packages.shared.redaction import SecretRedactor
    
    redactor = SecretRedactor()
    redacted_text, count = redactor.redact("API key: sk-abc123...")
    
    # Or redact entire tool results
    redacted_result = redactor.redact_tool_result(tool_result_dict)
"""

import re
from datetime import datetime
from typing import Any


class SecretRedactor:
    """
    Redact secrets from tool outputs before JSONL persistence.
    
    Patterns covered:
    - API keys (OpenAI, Google, GitHub, Slack, etc.)
    - AWS credentials (access keys, secret keys)
    - Private keys (RSA, EC)
    - Passwords in command output
    - Bearer tokens (JWT)
    - Database connection strings
    """
    
    # Common secret patterns (pattern, replacement)
    PATTERNS = [
        # === API Keys ===
        # OpenAI API keys (sk-...)
        (r'sk-[A-Za-z0-9]{20,}', '[REDACTED_OPENAI_API_KEY]'),
        
        # Google API keys (AIza...)
        (r'AIza[A-Za-z0-9_-]{20,}', '[REDACTED_GOOGLE_API_KEY]'),
        
        # GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_)
        (r'gh[pousr]_[A-Za-z0-9]{36}', '[REDACTED_GITHUB_TOKEN]'),
        
        # Slack tokens (xoxb-, xoxp-, xoxa-, xoxr-)
        (r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*', '[REDACTED_SLACK_TOKEN]'),
        
        # Generic API key patterns
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[A-Za-z0-9_-]{20,}', r'\1=[REDACTED_API_KEY]'),
        
        # === AWS Credentials ===
        # AWS Access Key ID
        (r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_ACCESS_KEY]'),
        
        # AWS Secret Access Key (40 char base64-like string, with context)
        (r'(?i)(aws[_-]?secret|secret[_-]?key)\s*[=:]\s*["\']?[A-Za-z0-9/+=]{40}', r'\1=[REDACTED_AWS_SECRET]'),
        
        # === Private Keys ===
        # RSA/EC Private Keys
        (r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', 
         '[REDACTED_PRIVATE_KEY]'),
        
        # === Passwords in Command Output ===
        # Password assignments (password=xxx, pwd: xxx, etc.)
        (r'(?i)(password|passwd|pwd|pass)\s*[=:]\s*["\']?[^\s"\']{4,}', r'\1=[REDACTED]'),
        
        # Database connection strings with passwords
        (r'(?i)(mongodb|postgres|mysql|redis):\/\/[^:]+:([^@]+)@', r'\1://\2:[REDACTED]@'),
        
        # === Bearer Tokens ===
        # JWT tokens (Bearer xxx.yyy.zzz)
        (r'Bearer [A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', 'Bearer [REDACTED_JWT]'),
        
        # Authorization headers
        (r'(?i)(authorization|auth)\s*[=:]\s*["\']?Bearer\s+[A-Za-z0-9_-]+', r'\1: Bearer [REDACTED]'),
        
        # === Connection Strings ===
        # Connection strings with passwords
        (r'(?i)(connection[_-]?string|conn[_-]?str)\s*[=:]\s*["\']?[^"\';\s]+', r'\1=[REDACTED]'),
        
        # === Personal Information ===
        # Email addresses (optional, can be disabled)
        # (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]'),
        
        # === Generic Patterns ===
        # Long base64 strings (potential secrets)
        (r'(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{60,}(?![A-Za-z0-9/+=])', '[REDACTED_BASE64]'),
    ]
    
    def __init__(
        self,
        custom_patterns: list[tuple[str, str]] | None = None,
        disable_email_redaction: bool = True,
    ):
        """
        Initialize the secret redactor.
        
        Args:
            custom_patterns: Additional (pattern, replacement) tuples to apply
            disable_email_redaction: If True, skip email redaction (default: True)
        """
        self.compiled_patterns: list[tuple[re.Pattern, str]] = []
        
        for pattern, replacement in self.PATTERNS:
            # Case-insensitive for password-related patterns
            flags = re.IGNORECASE if any(
                kw in pattern.lower() for kw in ['password', 'passwd', 'pwd', 'secret', 'auth']
            ) else 0
            self.compiled_patterns.append((re.compile(pattern, flags), replacement))
        
        # Add custom patterns
        if custom_patterns:
            for pattern, replacement in custom_patterns:
                self.compiled_patterns.append((re.compile(pattern), replacement))
    
    def redact(self, text: str) -> tuple[str, int]:
        """
        Redact secrets from text.
        
        Args:
            text: Input text that may contain secrets
            
        Returns:
            Tuple of (redacted_text, redaction_count)
        """
        if not text:
            return text, 0
        
        result = text
        total_redactions = 0
        
        for pattern, replacement in self.compiled_patterns:
            matches = pattern.findall(result)
            if matches:
                total_redactions += len(matches)
                result = pattern.sub(replacement, result)
        
        return result, total_redactions
    
    def redact_tool_result(self, tool_result: dict[str, Any]) -> dict[str, Any]:
        """
        Redact secrets from a tool result dictionary.
        
        Args:
            tool_result: Tool result dict with potential secrets in output/args
            
        Returns:
            Redacted tool result with metadata
        """
        if not tool_result:
            return tool_result
        
        # Deep copy to avoid mutating original
        import copy
        redacted = copy.deepcopy(tool_result)
        total_redactions = 0
        
        # Redact string fields commonly containing secrets
        string_fields = ['output', 'stdout', 'stderr', 'error', 'content', 'result', 'message']
        for key in string_fields:
            if key in redacted and isinstance(redacted[key], str):
                redacted[key], count = self.redact(redacted[key])
                total_redactions += count
        
        # Redact args (may contain passwords, tokens, etc.)
        if 'args' in redacted and isinstance(redacted['args'], dict):
            sensitive_keys = ['password', 'secret', 'token', 'api_key', 'apikey', 'auth', 'credential']
            for arg_key in list(redacted['args'].keys()):
                if any(sensitive in arg_key.lower() for sensitive in sensitive_keys):
                    if isinstance(redacted['args'][arg_key], str):
                        redacted['args'][arg_key] = '[REDACTED]'
                        total_redactions += 1
        
        # Redact headers (may contain Authorization tokens)
        if 'headers' in redacted and isinstance(redacted['headers'], dict):
            sensitive_headers = ['authorization', 'auth', 'x-api-key', 'x-auth-token']
            for header_key in list(redacted['headers'].keys()):
                if any(sensitive in header_key.lower() for sensitive in sensitive_headers):
                    redacted['headers'][header_key] = '[REDACTED]'
                    total_redactions += 1
        
        # Add redaction metadata if any redactions were made
        if total_redactions > 0:
            redacted['_redaction_metadata'] = {
                'redacted_count': total_redactions,
                'redacted_at': datetime.now().isoformat(),
                'redactor_version': '1.0.0',
            }
        
        return redacted
    
    def redact_dict_recursive(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively redact secrets from a nested dictionary.
        
        Args:
            data: Nested dictionary that may contain secrets
            
        Returns:
            Redacted dictionary
        """
        import copy
        result = copy.deepcopy(data)
        
        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, str):
                    result[key], _ = self.redact(value)
                elif isinstance(value, dict):
                    result[key] = self.redact_dict_recursive(value)
                elif isinstance(value, list):
                    result[key] = [
                        self.redact_dict_recursive(item) if isinstance(item, dict)
                        else self.redact(item)[0] if isinstance(item, str)
                        else item
                        for item in value
                    ]
        
        return result


# Global singleton instance
_redactor_instance: SecretRedactor | None = None


def get_redactor() -> SecretRedactor:
    """Get or create the global redactor instance."""
    global _redactor_instance
    if _redactor_instance is None:
        _redactor_instance = SecretRedactor()
    return _redactor_instance


def redact_text(text: str) -> tuple[str, int]:
    """Convenience function to redact text using global redactor."""
    return get_redactor().redact(text)


def redact_tool_result(tool_result: dict[str, Any]) -> dict[str, Any]:
    """Convenience function to redact tool results using global redactor."""
    return get_redactor().redact_tool_result(tool_result)
