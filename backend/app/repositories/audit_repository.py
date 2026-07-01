from backend.app.models import database as db


class AuditRepository:
    def log(self, user_id: int | None, action: str, details: str | None = None, ip: str | None = None) -> None:
        db.log_audit(user_id=user_id, action=action, details=details, ip=ip)
