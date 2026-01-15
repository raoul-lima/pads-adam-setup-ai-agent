import hashlib

def get_user_id_from_email(email: str) -> str:
    """Generate a consistent user_id from an email address."""
    return hashlib.sha256(email.encode('utf-8')).hexdigest()