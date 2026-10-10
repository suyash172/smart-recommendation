import logging

from app.db.repository import DecisionRepository

logger = logging.getLogger(__name__)


class KillSwitch:
    KEY = "kill_switch"

    def __init__(self, repo: DecisionRepository):
        self._repo = repo

    def is_active(self) -> bool:
        """Fail-safe: if the state cannot be read, behave as if the switch is ON."""
        try:
            setting = self._repo.get_setting(self.KEY)
        except Exception:
            logger.exception("Could not read kill switch state; failing safe (treating as ACTIVE)")
            return True
        return setting is not None and setting.value == "on"

    def set_active(self, active: bool, updated_by: str) -> dict:
        self._repo.set_setting(self.KEY, "on" if active else "off", updated_by)
        logger.warning("Kill switch set to %s by %s", "ON" if active else "OFF", updated_by)
        return self.status()

    def status(self) -> dict:
        setting = self._repo.get_setting(self.KEY)
        if setting is None:
            return {"active": False, "updated_by": None, "updated_at": None}
        return {
            "active": setting.value == "on",
            "updated_by": setting.updated_by,
            "updated_at": setting.updated_at,
        }