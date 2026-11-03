"""Pure resolution engine for Asymmetric Group.

This module intentionally has **no Home Assistant imports** so it can be
unit-tested standalone. All HA-facing code translates its data into the
plain dicts used here.

Vocabulary
----------
config dict keys:
    base_members, power_on_members, power_off_members, attribute_members,
    state_members, hide_members, all_entities

toggle dict keys:
    power, attributes, state  (bools)

runtime state dict (used by apply_sparse_preset / snapshots):
    {
        "toggles": {"power": bool, "attributes": bool, "state": bool},
        "subgroups": {
            "power_on_members": [...], "power_off_members": [...],
            "attribute_members": [...], "state_members": [...],
        },
        "last_applied_preset": str | None,
    }

preset dict (SPARSE):
    Keys ``asymmetric_power`` / ``asymmetric_attributes`` /
    ``asymmetric_state`` for toggles and the four ``*_members`` keys for
    member lists. A key that is *present* is applied — including an
    explicit ``False`` or an empty list. A key that is *absent* leaves
    the current value untouched.
"""

from __future__ import annotations

import copy

MEMBER_KEYS = (
    "power_on_members",
    "power_off_members",
    "attribute_members",
    "state_members",
)

# preset toggle key -> runtime toggle key
_PRESET_TOGGLE_MAP = {
    "asymmetric_power": "power",
    "asymmetric_attributes": "attributes",
    "asymmetric_state": "state",
}


def _dedup(items):
    """Order-preserving de-duplication."""
    seen = set()
    out = []
    for item in items or []:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _filtered(subgroup, base):
    """Subgroup intersected with base: subgroup order kept, deduped."""
    base_set = set(base)
    return _dedup([item for item in subgroup or [] if item in base_set])


def resolve_sets(config, toggles):
    """Resolve the effective member set for each dimension.

    Returns a dict with keys ``power_on``, ``power_off``, ``attributes``
    and ``state``. When a dimension's toggle is off, that dimension
    resolves to the full base set; when on, to its (base-filtered)
    subgroup.
    """
    base = _dedup(config.get("base_members"))
    toggles = toggles or {}
    return {
        "power_on": (
            _filtered(config.get("power_on_members"), base)
            if toggles.get("power")
            else list(base)
        ),
        "power_off": (
            _filtered(config.get("power_off_members"), base)
            if toggles.get("power")
            else list(base)
        ),
        "attributes": (
            _filtered(config.get("attribute_members"), base)
            if toggles.get("attributes")
            else list(base)
        ),
        "state": (
            _filtered(config.get("state_members"), base)
            if toggles.get("state")
            else list(base)
        ),
    }


def plan_turn_on(sets, currently_on, has_attributes):
    """Plan a turn_on call as (activate, attribute_only).

    ``activate`` is the power-ON set: those members are switched on
    (with any attributes in the call). ``attribute_only`` is the set of
    attribute-scope members that are *already on* but not being
    activated: they receive the attributes without being switched on —
    attribute application never activates a light. When the call carries
    no attributes there is nothing to apply, so ``attribute_only`` is
    empty. The caller issues at most these two batched service calls.
    """
    activate = list(sets.get("power_on") or [])
    attribute_only = []
    if has_attributes:
        activate_set = set(activate)
        currently_on = set(currently_on or ())
        attribute_only = [
            member
            for member in sets.get("attributes") or []
            if member in currently_on and member not in activate_set
        ]
    return activate, attribute_only


def compute_group_state(member_states, all_entities):
    """Compute group state from member states, mirroring core groups.

    ``member_states`` holds state strings ("on"/"off"/"unknown"/
    "unavailable") or None for a missing state (treated as unknown).

    any-mode (all_entities=False):
        unavailable if all members unavailable; unknown if all members
        unknown/unavailable; on if at least one on; else off.
    all-mode (all_entities=True):
        unavailable if all members unavailable; unknown if at least one
        member unknown/unavailable; on if all members on; else off.
    """
    states = [state if state is not None else "unknown" for state in member_states]
    if not states:
        return "unknown"

    if all(state == "unavailable" for state in states):
        return "unavailable"

    if all_entities:
        if any(state in ("unknown", "unavailable") for state in states):
            return "unknown"
        return "on" if all(state == "on" for state in states) else "off"

    if all(state in ("unknown", "unavailable") for state in states):
        return "unknown"
    return "on" if any(state == "on" for state in states) else "off"


def apply_sparse_preset(runtime_state, preset, base):
    """Apply a sparse preset dict to a runtime state dict.

    Returns a *new* runtime state dict; the input is not mutated.
    Present keys are applied (explicit False and empty member lists
    included); absent keys are left unchanged. Member lists are
    filtered to ``base``.
    """
    new_state = copy.deepcopy(runtime_state)
    new_state.setdefault("toggles", {})
    new_state.setdefault("subgroups", {})
    preset = preset or {}
    base = _dedup(base)

    for preset_key, toggle_key in _PRESET_TOGGLE_MAP.items():
        if preset_key in preset:
            new_state["toggles"][toggle_key] = bool(preset[preset_key])

    for member_key in MEMBER_KEYS:
        if member_key in preset:
            new_state["subgroups"][member_key] = _filtered(preset[member_key], base)

    return new_state


def mean_int(values):
    """Rounded mean of a list of ints, or None when empty."""
    values = list(values or [])
    if not values:
        return None
    return int(round(sum(values) / len(values)))


def mean_float(values):
    """Mean of a list of numbers, or None when empty."""
    values = list(values or [])
    if not values:
        return None
    return sum(values) / len(values)
