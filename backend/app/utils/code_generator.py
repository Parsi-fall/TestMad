import secrets
import string

# Characters that are visually distinct and easy to read/type manually
# Excluded: 0, O, 1, I, L
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_ticket_code(length: int = 6) -> str:
    """Generate a readable ticket code, e.g. 'TKT-8X4M9K'."""
    random_part = "".join(secrets.choice(ALPHABET) for _ in range(length))
    return f"TKT-{random_part}"
