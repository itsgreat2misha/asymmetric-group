# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Test infrastructure: bumped the Home Assistant test harness to
  pytest-homeassistant-custom-component 0.13.375 (Home Assistant 2026.10.4)
  and run the HA-level tests on Python 3.14 in CI.

### Fixed

- Reported the group light's member colour-temperature range in kelvin
  (`min_color_temp_kelvin` / `max_color_temp_kelvin`, reduced from member
  capabilities with a 2000/6500 K fallback) instead of serving the legacy
  mireds defaults, which warned on state writes.

## [1.3.0] - 2026-11-03

### Changed

- Enforce Power Scope settle semantics: a scope change (toggle flip,
  preset apply, or `set_members`) no longer returns until the lights
  enforcement turned on or off have registered their new states. The wait
  is event-driven; lights already in the desired state or unavailable are
  skipped, and a light that does not settle is dropped from the wait and
  named in a single aggregated warning in the Home Assistant log.

### Removed

- The timed scope re-assertion added in 1.2.1 and adjusted in 1.2.2 and
  1.2.3 (most recently a single recheck at ~5 s).

## [1.2.3] - 2026-11-03

### Changed

- Scope re-assertion after an enforcement event is now a single recheck
  at ~5 s (was ~8 s, ~20 s and ~50 s).

## [1.2.2] - 2026-11-03

### Changed

- Scope re-assertion checks now run at ~8 s, ~20 s and ~50 s after an
  enforcement event (was ~20 s and ~50 s), so a room reaches its narrowed
  state sooner.

## [1.2.1] - 2026-11-03

### Fixed

- After Enforce Power Scope turns lights off, the scope is re-asserted
  for exactly those lights at ~20 s and ~50 s, so another integration
  re-lighting a just-excluded light moments after a scope change does not
  undo the enforcement. The re-checks are evaluated against the scope as
  it stands when they run.

## [1.2.0] - 2026-11-03

### Added

- Enforce Power Scope companion switch (default off). When on, a change
  to the group's effective Power-ON set — flipping Asymmetric power,
  editing sets, applying a preset, or calling `set_members` — reconciles
  lights that are already on: members that fell out of the set and are on
  are turned off; members that entered the set are turned on only if the
  group was lit through its old set (dark rooms are staged, never
  struck); a light that is on but was in neither set is left alone.
  Enforcement never fires on startup/restart.
- The enforce toggle is exposed in group attributes, presets (sparse key
  `enforce_power_scope`), the `set_members` service, and the
  config/options flow.

### Changed

- README gained a full worked example (bedroom day/night modes)
  explaining every switch.

## [1.1.1] - 2026-11-03

### Fixed

- Groups mixing an on/off-only light with dimmable/colour lights were
  refused by Home Assistant because `ONOFF` cannot be combined with other
  colour modes. `ONOFF` is now dropped from the group's supported modes
  when other modes exist, and the reported colour mode is always one of
  the supported modes.

## [1.1.0] - 2026-11-03

### Added

- `asymmetric_group.set_members` service: change a group's toggles and
  member sets directly; only the fields passed change.
- `asymmetric_group.list_presets` service: returns the preset library as
  a service response.

### Changed

- README rewritten for end users and updated for the current setup flow.

## [1.0.2] - 2026-11-03

### Fixed

- When a group was on via its State scope while no Attribute-scope member
  was on, the light reported no colour mode and Home Assistant dropped
  the state write (the group appeared stuck off). The group now falls
  back to lit members for its reported colour mode and displayed
  attributes.

## [1.0.1] - 2026-11-03

### Fixed

- Config/options flow: subgroup member selectors are now shown as their
  own steps, only for dimensions whose toggle is enabled (previously all
  subgroups were always visible). Runtime unchanged from 1.0.0.

## [1.0.0] - 2026-11-03

### Added

- First release of Asymmetric Group: Home Assistant light groups with
  per-dimension member sets (power on/off, attributes, state),
  runtime companion-switch toggles, and a global sparse preset library
  with apply/save/delete services.
