"""Per-group runtime state for Asymmetric Group.

A GroupRuntime holds everything that can change *without* editing the
config entry: the three dimension toggles, the four subgroup member
lists (as possibly modified by presets) and ``last_applied_preset``.

Runtime state is seeded from the config entry at setup and persisted in
a per-entry Store, so preset-applied member sets survive a restart.
Editing the entry's options clears that Store, re-seeding from config.
"""

from __future__ import annotations

import copy
from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import engine
from .const import (
    CONF_ALL_ENTITIES,
    CONF_ASYMMETRIC_ATTRIBUTES,
    CONF_ASYMMETRIC_POWER,
    CONF_ASYMMETRIC_STATE,
    CONF_ATTRIBUTE_MEMBERS,
    CONF_BASE_MEMBERS,
    CONF_HIDE_MEMBERS,
    CONF_NAME,
    CONF_POWER_OFF_MEMBERS,
    CONF_POWER_ON_MEMBERS,
    CONF_STATE_MEMBERS,
    ENTRY_STORE_VERSION,
    MEMBER_KEYS,
    TOGGLE_ATTRIBUTES,
    TOGGLE_POWER,
    TOGGLE_STATE,
    entry_store_key,
)

# config default-toggle key -> runtime toggle key
_CONFIG_TOGGLE_MAP = {
    CONF_ASYMMETRIC_POWER: TOGGLE_POWER,
    CONF_ASYMMETRIC_ATTRIBUTES: TOGGLE_ATTRIBUTES,
    CONF_ASYMMETRIC_STATE: TOGGLE_STATE,
}


class GroupRuntime:
    """Mutable runtime state for one Asymmetric Group config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str, config: dict) -> None:
        self.hass = hass
        self.entry_id = entry_id
        # Merged config entry data+options; treated as read-only here.
        self.config = config
        self._store: Store = Store(
            hass, ENTRY_STORE_VERSION, entry_store_key(entry_id)
        )
        self._listeners: list[Callable[[], None]] = []
        # entity_id of the group's light entity, set once it is added.
        self.entity_id: str | None = None

        # --- seed from config -------------------------------------------
        self.toggles: dict[str, bool] = {
            toggle_key: bool(config.get(config_key, False))
            for config_key, toggle_key in _CONFIG_TOGGLE_MAP.items()
        }
        self.subgroups: dict[str, list[str]] = {
            key: list(config.get(key) or []) for key in MEMBER_KEYS
        }
        self.last_applied_preset: str | None = None

    # ------------------------------------------------------------------
    # Plain config accessors
    @property
    def name(self) -> str:
        return self.config.get(CONF_NAME) or "Asymmetric Group"

    @property
    def base_members(self) -> list[str]:
        return list(self.config.get(CONF_BASE_MEMBERS) or [])

    @property
    def hide_members(self) -> bool:
        return bool(self.config.get(CONF_HIDE_MEMBERS, False))

    @property
    def all_entities(self) -> bool:
        return bool(self.config.get(CONF_ALL_ENTITIES, False))

    # ------------------------------------------------------------------
    # Persistence
    def _state_dict(self) -> dict:
        """Runtime state in engine/snapshot shape."""
        return {
            "toggles": dict(self.toggles),
            "subgroups": copy.deepcopy(self.subgroups),
            "last_applied_preset": self.last_applied_preset,
        }

    async def async_load(self) -> None:
        """Overlay persisted runtime state (if any) onto the config seed."""
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return
        toggles = data.get("toggles")
        if isinstance(toggles, dict):
            for key in self.toggles:
                if key in toggles:
                    self.toggles[key] = bool(toggles[key])
        subgroups = data.get("subgroups")
        if isinstance(subgroups, dict):
            base = set(self.base_members)
            for key in MEMBER_KEYS:
                if key in subgroups:
                    # Keep only members that are still in base.
                    self.subgroups[key] = [
                        m for m in subgroups[key] or [] if m in base
                    ]
        if "last_applied_preset" in data:
            self.last_applied_preset = data.get("last_applied_preset")

    async def async_save(self) -> None:
        await self._store.async_save(self._state_dict())

    async def async_clear_store(self) -> None:
        """Drop persisted runtime state so the next setup re-seeds."""
        # TODO(live-verify): Store.async_remove exists on current HA;
        # confirm behaviour when no file exists yet.
        await self._store.async_remove()

    # ------------------------------------------------------------------
    # Listeners (entities subscribe to runtime changes)
    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(callback)

        def _remove() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return _remove

    def _notify(self) -> None:
        for callback in list(self._listeners):
            callback()

    # ------------------------------------------------------------------
    # Mutations (each persists + notifies)
    async def async_set_toggle(self, toggle_key: str, value: bool) -> None:
        if self.toggles.get(toggle_key) == value:
            self._notify()
            return
        self.toggles[toggle_key] = bool(value)
        await self.async_save()
        self._notify()

    async def async_apply_preset(self, preset: dict, preset_name: str) -> None:
        """Apply a sparse preset and record it as last applied.

        Only the ``last_applied_preset`` label is recorded — there is
        deliberately no drift/Custom tracking: later manual changes do
        not clear the label.
        """
        new_state = engine.apply_sparse_preset(
            self._state_dict(), preset, self.base_members
        )
        self.toggles = {k: bool(v) for k, v in new_state["toggles"].items()}
        self.subgroups = new_state["subgroups"]
        self.last_applied_preset = preset_name
        await self.async_save()
        self._notify()

    def snapshot_preset(self) -> dict:
        """Full (non-sparse) preset snapshot of the current runtime."""
        snapshot: dict = {
            CONF_ASYMMETRIC_POWER: self.toggles[TOGGLE_POWER],
            CONF_ASYMMETRIC_ATTRIBUTES: self.toggles[TOGGLE_ATTRIBUTES],
            CONF_ASYMMETRIC_STATE: self.toggles[TOGGLE_STATE],
        }
        for key in MEMBER_KEYS:
            snapshot[key] = list(self.subgroups[key])
        return snapshot

    # ------------------------------------------------------------------
    # Resolution for the light entity
    def effective_sets(self) -> dict[str, list[str]]:
        """Resolve effective member sets via the pure engine."""
        engine_config = {CONF_BASE_MEMBERS: self.base_members, **self.subgroups}
        return engine.resolve_sets(engine_config, self.toggles)

    def register_entity_id(self, entity_id: str) -> None:
        """Record the light entity_id so services can find this runtime."""
        self.entity_id = entity_id
        domain_data = self.hass.data.setdefault(
            "asymmetric_group", {}
        )
        by_entity = domain_data.setdefault("runtimes_by_entity", {})
        by_entity[entity_id] = self

    def unregister_entity_id(self) -> None:
        if self.entity_id is None:
            return
        by_entity = (
            self.hass.data.get("asymmetric_group", {}).get("runtimes_by_entity", {})
        )
        if by_entity.get(self.entity_id) is self:
            del by_entity[self.entity_id]
        self.entity_id = None
