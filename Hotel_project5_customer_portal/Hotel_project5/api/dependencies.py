"""Dependencies dùng chung cho các route bảo vệ."""

from api.routers.auth import get_current_user, require_admin, require_customer

__all__ = ["get_current_user", "require_admin", "require_customer"]
