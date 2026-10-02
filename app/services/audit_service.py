# app/services/audit_service.py
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

def log_admin_action(
    db: Session, 
    admin_id: int, 
    action: str, 
    target_type: str = None, 
    target_id: int = None, 
    details: str = None
):
    """Creates a permanent record of an admin's action."""
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details
    )
    db.add(log)
    db.commit()