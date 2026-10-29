# audit/services.py
from audit.models import AuditLog


def log_action(request, action, target=None, target_type="", target_id="", metadata=None):
    if target is not None and not target_type:
        target_type = target.__class__.__name__
        target_id = str(getattr(target, "pk", ""))
    user = getattr(request, "user", None)
    if user is not None and not user.is_authenticated:
        user = None
    AuditLog.objects.create(
        user=user,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
        ip_address=getattr(request, "_audit_ip", None),
        user_agent=getattr(request, "_audit_ua", ""),
    )
