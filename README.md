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
3. Optionally enable **Hide members** (hide the individual lights, like a regular group), **All entities** (the group is only "on" when *all* of its state lights are on), and **Enforce power scope** (when the Power-ON set changes, reconcile lights that are already on — see *Enforce power scope* below).

You can change all of this later under the group's **Configure** button. Settings for behaviours you didn't enable simply use all the base lights.

## How it works

Each behaviour has its own switch on the group's device page — **Asymmetric power**, **Asymmetric attributes**, and **Asymmetric state** — plus a fourth, **Enforce power scope**, described below. While a switch is off, that behaviour uses all the base lights, exactly like a regular group. Turn it on, and that behaviour uses its own smaller set instead.

| Behaviour | Switch on | Switch off |
|---|---|---|
| Power | Turn-on uses the Power-ON lights; turn-off uses the Power-OFF lights | Both use all base lights |
| Attributes | Brightness/colour changes go to the Attribute lights | Changes go to all base lights |
| State | The group's on/off state and reported brightness/colour come from the State lights | They come from all base lights |

Two guarantees hold at all times:

- **Changing brightness or colour never turns a light on.** If a brightness change reaches the group, lights in the attribute set that are already on get the new brightness — lights that are off stay off, and nothing flashes on and off.
- **The group's light list always shows all base lights** (in its `entity_id` attribute), so `expand()` and templates keep working as they do with a regular group. Extra attributes (`effective_power_on_members`, `effective_attribute_members`, and so on) show which sets are currently in effect.

Group lights can't be members of an Asymmetric Group — add the individual lights instead.

### Enforce power scope

A fourth switch, **Enforce power scope** (off by default), reconciles lights that are already on when the effective Power-ON set changes — by flipping the Asymmetric power switch, editing the sets, applying a preset, or calling `set_members`:

- Lights that **fell out** of the Power-ON set and are on are turned off.
- Lights that **entered** the set are turned on, but only if the group was actually lit through its old set (at least one old-set light on). If the group was dark, the new set is only staged — nothing turns on.
- A light that is on but was in neither the old nor the new set (turned on by hand while excluded) is left alone, and doesn't count as "the group was lit".

Enforcement never fires on startup or restart — only on a live change — and flipping the Enforce switch itself changes nothing until the next scope change. One refinement: when enforcement turns lights off, it re-asserts the scope once, ~5 seconds later, for exactly those lights — covering the case where another integration was mid-apply as the scope changed and re-lights one of them (Adaptive Lighting does this when its switches toggle). After that single recheck the matter is closed: a light that comes on later stays on. The re-checks use the scope as it stands when they run, so changing your mind (widening the scope again) cancels their effect. A typical use: a lighting theme narrows the group for a "Dim" scene; with enforcement on, entering the scene also switches off the room's other lights that happened to be on, instead of only filtering the next turn-on.

## Controlling groups from automations

Everything about a group can be driven from automations and scripts:

- **Flip a behaviour on or off** with the group's switches, e.g. an "evening mode" automation turns on *Asymmetric power* and from then on the group turns on partially but always turns off fully.
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

## Example: one bedroom, two personalities

A bedroom has four recessed lights, `light.bedroom_1` … `light.bedroom_4`. Light 3 is the one whose position gives a soft, low glow — enough to move around at night without waking anyone. During the day the room should behave like any normal room; at night, "the bedroom lights" should mean light 3 only.

Create an Asymmetric Group **Bedroom lights** with all four lights as base members:

- **Power-ON set:** `light.bedroom_3` · **Power-OFF set:** all four
- **Asymmetric attributes / state:** off (they use all base lights)
- **Enforce power scope:** on

A lighting automation flips the group's **Asymmetric power** switch: off for the daytime/evening themes, on for the night ("Dim") theme. Adaptive Lighting is configured with the four individual lights, so it adapts each light that is on, whichever mode the group is in.

What happens, switch by switch:

- **Daytime — Asymmetric power off.** The group is an ordinary group. Turning it on lights all four; Adaptive Lighting adapts all four. Nothing about the group is special.
- **The night theme engages — Asymmetric power flips on.** The Power-ON set shrinks to light 3. Because **Enforce power scope** is on, the change is reconciled immediately: if all four lights were on, 1, 2 and 4 turn off and light 3 stays — the room drops to its night light instead of waiting for the next turn-on to be filtered. If the room was dark, nothing turns on; the narrower set is simply staged for the next command.
- **"Turn on the bedroom lights" at night — Asymmetric power's job.** Only light 3 lights. This is the core trick: the group is filtered at the group itself, so it works identically from voice, a dashboard, an automation, or a wall switch that targets the group.
- **Someone turns light 2 on by hand.** It comes on (direct control of a light is never blocked) and Adaptive Lighting adapts it. But **"turn off the bedroom lights" still switches all four off**, including the hand-lit light 2 — the Power-OFF set is the full base set, so a group off always sweeps the whole room.
- **Morning — Asymmetric power flips back off.** The set widens to all four again. With enforcement on, if light 3 is still lit the other three come on with it — the room comes up as a whole; if the room is dark, nothing happens and the group is a plain group again.

### Where the other two switches earn their keep

- **Asymmetric attributes** — a bathroom group of ceiling lights plus a vanity light. The vanity is set bright for shaving and shouldn't be dragged along when a scene dims the group for a bath. Put the ceiling lights in the Attribute set and leave the vanity out: brightness and colour changes to the group adjust the ceiling lights (the ones that are on), while the vanity keeps its level. It still turns on and off with the group — only attribute changes skip it.
- **Asymmetric state** — a hallway group that also includes the hall closet light, so "hallway off" sweeps the closet too. The closet shouldn't make the hallway read as *on* on a dashboard just because someone left it lit. Put only the ceiling lights in the State set: the group's on/off state and reported brightness come from them, and the closet light is invisible to the group's state while remaining a full member for power.

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
