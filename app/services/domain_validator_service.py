from app.constants.blocked_domains import BLOCKED_EMAIL_DOMAINS


class DomainValidatorService:

    def is_valid_company_domain(self, email: str) -> bool:
        if "@" not in email:
            return False
        domain = email.split("@")[1].lower()
        return domain not in BLOCKED_EMAIL_DOMAINS

    def extract_domain(self, email: str) -> str:
        return email.split("@")[1].lower()
