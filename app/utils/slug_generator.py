import re
import secrets


def generate_org_slug(domain: str) -> str:
    base = domain.split(".")[0]
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    suffix = secrets.token_hex(2)
    return f"{base}-{suffix}"


def generate_org_name_from_domain(domain: str) -> str:
    base = domain.split(".")[0]
    return base.replace("-", " ").replace("_", " ").title()
