# Asymmetric Group

A Home Assistant helper that makes a light group where **turning on, turning off, changing brightness/colour, and the group's on/off state can each involve a different set of lights** — and you can switch each of those behaviours on and off whenever you like.

In a regular light group, the same lights do everything. That makes a common wish impossible:

> In the evening, "turn on the bedroom lights" should light just one lamp — but "turn off the bedroom lights" must switch **everything** off, including a lamp someone turned on by hand.

With an Asymmetric Group that's just how the group is set up, so it works the same everywhere: voice assistants, dashboards, wall switches, and automations all talk to the group itself.

## Installation

1. In **HACS**, open **⋮ → Custom repositories** and add `https://github.com/itsgreat2misha/asymmetric-group` as an **Integration**.
2. Install **Asymmetric Group** from HACS and restart Home Assistant.
3. Go to **Settings → Devices & services → Helpers → Create helper → Asymmetric Group**.

Requires Home Assistant 2025.1.0 or newer.

## Setting up a group

1. **Name** the group and choose its **base members**: every light that should ever be controlled or watched through this group. Each of the smaller sets below is picked from these lights.
2. **Choose which behaviours should be asymmetric.** For each one you turn on, you'll be asked which lights it applies to:
   - **Power** — separate light sets for turning on and turning off.
   - **Attributes** — the lights that receive brightness and colour changes.
   - **State** — the lights that decide whether the group counts as "on", and whose brightness/colour the group reports.
3. Optionally enable **Hide members** (hide the individual lights, like a regular group) and **All entities** (the group is only "on" when *all* of its state lights are on).

You can change all of this later under the group's **Configure** button. Settings for behaviours you didn't enable simply use all the base lights.

## How it works

Each behaviour has its own switch on the group's device page — **Asymmetric power**, **Asymmetric attributes**, and **Asymmetric state**. While a switch is off, that behaviour uses all the base lights, exactly like a regular group. Turn it on, and that behaviour uses its own smaller set instead.

| Behaviour | Switch on | Switch off |
|---|---|---|
| Power | Turn-on uses the Power-ON lights; turn-off uses the Power-OFF lights | Both use all base lights |
| Attributes | Brightness/colour changes go to the Attribute lights | Changes go to all base lights |
| State | The group's on/off state and reported brightness/colour come from the State lights | They come from all base lights |

Two guarantees hold at all times:

- **Changing brightness or colour never turns a light on.** If a brightness change reaches the group, lights in the attribute set that are already on get the new brightness — lights that are off stay off, and nothing flashes on and off.
- **The group's light list always shows all base lights** (in its `entity_id` attribute), so `expand()` and templates keep working as they do with a regular group. Extra attributes (`effective_power_on_members`, `effective_attribute_members`, and so on) show which sets are currently in effect.

Group lights can't be members of an Asymmetric Group — add the individual lights instead.

## Controlling groups from automations

Everything about a group can be driven from automations and scripts:

- **Flip a behaviour on or off** with the group's three switches, e.g. an "evening mode" automation turns on *Asymmetric power* and from then on the group turns on partially but always turns off fully.
- **Change sets and switches on the fly** with the `asymmetric_group.set_members` action. Only the fields you include are changed:

```yaml
action: asymmetric_group.set_members
data:
  entity_id: light.bedroom_lights
  asymmetric_state: true
  state_members:
    - light.bedroom_3
```

- **Presets** (below) can be applied, saved, and deleted with actions, and the whole preset library can be read into a script variable — see the services list.

### Services

| Service | What it does |
|---|---|
| `asymmetric_group.set_members` | Change a group's switches and light sets. Only the fields you pass are changed. |
| `asymmetric_group.list_presets` | Returns the preset library (names and contents) as a response — use `response_variable` in scripts. |
| `asymmetric_group.apply_preset` | Apply a saved preset to a group (`entity_id`, `preset`). |
| `asymmetric_group.save_preset` | Save a group's current settings as a preset (`entity_id`, `preset`, optional `overwrite`). |
| `asymmetric_group.delete_preset` | Delete a preset from the library (`preset`). Groups that used it keep their settings. |

## Presets

A preset is a named bundle of settings — switch positions and light sets — kept in one library shared by all your Asymmetric Groups. Apply it to any group from an automation, a script, or the group's **Configure → Preset library** editor.

A preset only needs to contain the settings it should change. Settings it doesn't mention are left alone, which makes two styles possible:

- **Behaviour patterns** — e.g. a preset that only stores "Asymmetric power: on". Apply it to many groups to give them all the same behaviour, each keeping its own lights.
- **Full snapshots** — save a group's complete settings with `asymmetric_group.save_preset` and re-apply them later, or tweak the snapshot in the editor first.

Light sets in a preset are matched against each group's own base lights when applied, so a preset can never point a group at lights it doesn't have. After a preset is applied, the group's `last_applied_preset` attribute shows its name (just a label — editing the group afterwards doesn't remove it).

## Example

A bedroom has four lights. Create an Asymmetric Group "Bedroom lights" with all four as base members:

- Power-ON lights: `light.bedroom_3` only; Power-OFF lights: all four.
- Attribute and State lights: `light.bedroom_3`.

An evening automation turns on the group's three Asymmetric switches. Now:

- "Turn on the bedroom lights" lights only `light.bedroom_3`.
- Someone turns on `light.bedroom_2` by hand. It doesn't change the group's reported state or brightness — those come from `light.bedroom_3` — and a brightness change still goes to `light.bedroom_3` only.
- "Turn off the bedroom lights" switches **all four** off, including the hand-lit lamp.

When the automation turns the switches back off, the group is an ordinary group again.

## Good to know

- Only calls made **to the group itself** are affected. Anything that addresses the lights directly — an area or label target, a scene, or another integration — works exactly as before.
- If a behaviour's lights are all off while the group is on for another reason (say, the group is on because a State light is on, but no Attribute light is), the group reports its colour and brightness from whichever lights are actually on, so dashboards always show sensible values.
- Switching a behaviour on or off can change the group's reported on/off state without any light changing — for example, turning *Asymmetric state* off when a hand-lit lamp is on suddenly counts that lamp. That's inherent to choosing which lights define the state.
- Light groups only for now; member lights that are themselves groups are not supported.
- A group's current settings survive restarts. Editing the group under **Configure** resets it to the configured sets, discarding changes made by presets or `set_members` since — the Configure page is the starting point after every edit.

## FAQ

**Is this a replacement for the built-in Group helper?**
No — it sits next to it. Use regular groups unless you need different lights for different behaviours.

**What happens if I delete a preset?**
Nothing changes on any group. Applying a preset copies its settings into the group, so groups keep working without it.

**Can I create or delete groups from automations?**
Groups themselves are created in the UI like other helpers. Everything about an existing group — its switches, its light sets, and presets — is controllable from automations and scripts.

## License

MIT — see [LICENSE](LICENSE).
