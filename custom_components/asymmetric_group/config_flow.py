"""Config and options flow for Asymmetric Group.

Creation is a helper-style two-step flow:
  1. user  — name + base members (ALL lights involved in any way);
             group entities are rejected as members (no nesting in v1).
  2. sets  — default values for the three runtime toggles, the four
             subgroup member lists (prefilled with base), and the
             core-parity options hide_members / all_entities.

The options flow offers a menu:
  - "members": the same sets form; saving also clears the per-entry
    runtime store so runtime state re-seeds from the new config.
  - "presets": a central editor for the global preset library.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)
from homeassistant.helpers.storage import Store

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
    DOMAIN,
    ENTRY_STORE_VERSION,
    MEMBER_KEYS,
    entry_store_key,
)
from .presets import async_get_preset_store

_NEW_PRESET = "__new__"

_TOGGLE_PRESET_KEYS = (
    CONF_ASYMMETRIC_POWER,
    CONF_ASYMMETRIC_ATTRIBUTES,
    CONF_ASYMMETRIC_STATE,
)


def _light_selector() -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain="light", multiple=True))


def _find_group_members(hass: HomeAssistant, members: list[str]) -> list[str]:
    """Members that are themselves groups (state has an entity_id attr)."""
    groups = []
    for member in members:
        state = hass.states.get(member)
        if state is not None and "entity_id" in state.attributes:
            groups.append(member)
    return groups


def _sets_schema(defaults: dict) -> vol.Schema:
    """Schema for the subgroup/options form, prefilled from defaults."""
    base = list(defaults.get(CONF_BASE_MEMBERS) or [])
    return vol.Schema(
        {
            vol.Required(
                CONF_ASYMMETRIC_POWER,
                default=bool(defaults.get(CONF_ASYMMETRIC_POWER, False)),
            ): BooleanSelector(),
            vol.Required(
                CONF_ASYMMETRIC_ATTRIBUTES,
                default=bool(defaults.get(CONF_ASYMMETRIC_ATTRIBUTES, False)),
            ): BooleanSelector(),
            vol.Required(
                CONF_ASYMMETRIC_STATE,
                default=bool(defaults.get(CONF_ASYMMETRIC_STATE, False)),
            ): BooleanSelector(),
            vol.Required(
                CONF_POWER_ON_MEMBERS,
                default=list(defaults.get(CONF_POWER_ON_MEMBERS) or base),
            ): _light_selector(),
            vol.Required(
                CONF_POWER_OFF_MEMBERS,
                default=list(defaults.get(CONF_POWER_OFF_MEMBERS) or base),
            ): _light_selector(),
            vol.Required(
                CONF_ATTRIBUTE_MEMBERS,
                default=list(defaults.get(CONF_ATTRIBUTE_MEMBERS) or base),
            ): _light_selector(),
            vol.Required(
                CONF_STATE_MEMBERS,
                default=list(defaults.get(CONF_STATE_MEMBERS) or base),
            ): _light_selector(),
            vol.Required(
                CONF_HIDE_MEMBERS,
                default=bool(defaults.get(CONF_HIDE_MEMBERS, False)),
            ): BooleanSelector(),
            vol.Required(
                CONF_ALL_ENTITIES,
                default=bool(defaults.get(CONF_ALL_ENTITIES, False)),
            ): BooleanSelector(),
        }
    )


class AsymmetricGroupConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Asymmetric Group."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return AsymmetricGroupOptionsFlow(config_entry)

    def __init__(self) -> None:
        self._user_data: dict = {}

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            base_members = list(user_input.get(CONF_BASE_MEMBERS) or [])
            if _find_group_members(self.hass, base_members):
                # Nested groups are rejected in v1: their expansion
                # semantics under asymmetric sets are undefined.
                errors[CONF_BASE_MEMBERS] = "group_member_not_allowed"
            else:
                self._user_data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_BASE_MEMBERS: base_members,
                }
                return await self.async_step_sets()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): TextSelector(),
                    vol.Required(CONF_BASE_MEMBERS): _light_selector(),
                }
            ),
            errors=errors,
        )

    async def async_step_sets(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            data = {**self._user_data, **user_input}
            return self.async_create_entry(title=data[CONF_NAME], data=data)
        return self.async_show_form(
            step_id="sets",
            data_schema=_sets_schema(self._user_data),
        )


class AsymmetricGroupOptionsFlow(OptionsFlow):
    """Options: member sets + the global preset editor."""

    def __init__(self, config_entry) -> None:
        # TODO(live-verify): current HA manages OptionsFlow.config_entry
        # itself; storing the entry here is the long-standing pattern
        # and harmless, but confirm no deprecation on the target version.
        self._entry = config_entry
        self._preset_name: str | None = None
        self._preset_is_new = False

    @property
    def _config_entry(self):
        return getattr(self, "config_entry", None) or self._entry

    # ------------------------------------------------------------------
    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["members", "presets"],
        )

    # ------------------------------------------------------------------
    # Members
    async def async_step_members(self, user_input: dict | None = None) -> ConfigFlowResult:
        entry = self._config_entry
        merged = {**entry.data, **entry.options}
        if user_input is not None:
            # Options edits re-seed runtime state: clear the per-entry
            # runtime store so stored toggles/subgroups don't shadow
            # the new config after the reload triggered by saving.
            store = Store(
                self.hass, ENTRY_STORE_VERSION, entry_store_key(entry.entry_id)
            )
            # TODO(live-verify): Store.async_remove with no existing file.
            await store.async_remove()
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="members",
            data_schema=_sets_schema(merged),
        )

    # ------------------------------------------------------------------
    # Presets
    async def async_step_presets(self, user_input: dict | None = None) -> ConfigFlowResult:
        return await self.async_step_presets_pick(user_input)

    async def async_step_presets_pick(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        store = await async_get_preset_store(self.hass)
        names = store.list_presets()
        if user_input is not None:
            chosen = user_input["preset"]
            self._preset_is_new = chosen == _NEW_PRESET
            self._preset_name = None if self._preset_is_new else chosen
            return await self.async_step_presets_edit()
        return self.async_show_form(
            step_id="presets_pick",
            data_schema=vol.Schema(
                {
                    vol.Required("preset", default=_NEW_PRESET): SelectSelector(
                        SelectSelectorConfig(options=names + [_NEW_PRESET])
                    ),
                }
            ),
        )

    def _preset_edit_schema(self, existing: dict) -> vol.Schema:
        fields: dict = {}
        if self._preset_is_new:
            fields[vol.Required("preset_name")] = TextSelector()
        for key in _TOGGLE_PRESET_KEYS:
            if key in existing:
                default = "on" if existing[key] else "off"
            else:
                default = "unchanged"
            fields[vol.Required(key, default=default)] = SelectSelector(
                SelectSelectorConfig(options=["unchanged", "on", "off"])
            )
        for key in MEMBER_KEYS:
            fields[
                vol.Required(f"{key}_include", default=key in existing)
            ] = BooleanSelector()
            fields[
                vol.Optional(key, default=list(existing.get(key) or []))
            ] = _light_selector()
        if not self._preset_is_new:
            fields[vol.Optional("delete_preset", default=False)] = BooleanSelector()
        return vol.Schema(fields)

    async def async_step_presets_edit(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        store = await async_get_preset_store(self.hass)
        existing = {} if self._preset_is_new else (store.get(self._preset_name or "") or {})
        errors: dict[str, str] = {}

        if user_input is not None:
            if not self._preset_is_new and user_input.get("delete_preset"):
                await store.async_delete_preset(self._preset_name or "")
                return await self.async_step_init()

            name = self._preset_name
            if self._preset_is_new:
                name = (user_input.get("preset_name") or "").strip()
                if not name:
                    errors["preset_name"] = "preset_name_required"
            if not errors:
                # Build the SPARSE preset: a field only lands in the
                # dict when the user chose to include it.
                preset: dict = {}
                for key in _TOGGLE_PRESET_KEYS:
                    choice = user_input.get(key, "unchanged")
                    if choice != "unchanged":
                        preset[key] = choice == "on"
                for key in MEMBER_KEYS:
                    if user_input.get(f"{key}_include"):
                        preset[key] = list(user_input.get(key) or [])
                await store.async_save_preset(name or "", preset)
                return await self.async_step_init()

        return self.async_show_form(
            step_id="presets_edit",
            data_schema=self._preset_edit_schema(existing),
            errors=errors,
        )

