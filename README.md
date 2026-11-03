# Asymmetric Group

A Home Assistant helper that creates a light group where **turn-on, turn-off, attribute changes, and group state can each follow a different member set** — and each of those behaviours can be switched on or off at runtime.

In a regular light group, every dimension uses the same members: turning the group on turns everything on, the group reads "on" if any member is on, and a brightness change goes to all members. An Asymmetric Group lets you split that up. The classic use case:

> In a dimmed/evening mode, "turn on the bedroom lights" should light only one lamp — but "turn off the bedroom lights" must always switch **everything** off, including a lamp someone turned on manually.

That is impossible to express with a regular group. With an Asymmetric Group it is a configuration, not an automation — so it works identically from voice assistants, dashboards, wall switches, and automations, because everything targets the group entity itself.

## Installation

### Via HACS (custom repository)

1. Open **HACS → Integrations → ⋮ (top right) → Custom repositories**.
2. Add `https://github.com/itsgreat2misha/asymmetric-group` with category **Integration**.
3. Search HACS for **Asymmetric Group** and install it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → Asymmetric Group**.

### Manual

Copy `custom_components/asymmetric_group/` into your Home Assistant `custom_components/` directory, restart, and add the integration from **Settings → Devices & services**.

Requires Home Assistant 2025.1.0 or newer.

## Creating a group

**Settings → Devices & services → Helpers → Create helper → Asymmetric Group** (or add it as an integration — it is a helper-type integration).

1. **Name and base members.** Base members are *all* lights involved in the group in any way — every light that should ever be controlled or observed through this group. (Group entities cannot be members; add the individual lights instead.)
2. **Member sets and defaults.** For each dimension you pick a subgroup and the default state of its toggle:
   - **Power-ON members** — used by `turn_on` while *Asymmetric power* is on.
   - **Power-OFF members** — used by `turn_off` while *Asymmetric power* is on.
   - **Attribute members** — receive brightness/colour changes while *Asymmetric attributes* is on.
   - **State members** — decide the group's on/off state and reported brightness/colour while *Asymmetric state* is on.
   - **Hide members** and **All entities** behave exactly like the same options on a regular group (see below).

Subgroups are always filtered to the base set. Editing a group's sets later is under the integration's **Configure** dialog.

## The three dimensions

Each dimension has a runtime toggle, exposed both as a companion switch on the group's device (see below) and as a preset target. When a dimension's toggle is **off**, that dimension simply uses the full base set — the group behaves like a regular group in that respect.

| Dimension | Toggle on | Toggle off |
|---|---|---|
| **Power** | `turn_on` → Power-ON members; `turn_off` → Power-OFF members | both use base members |
| **Attributes** | attribute changes apply to Attribute members | apply to base members |
| **State** | `is_on` and reported brightness/colour computed over State members | computed over base members |

One rule always holds: **attribute changes never turn a light on.** If a `turn_on` call with attributes (say, a brightness) reaches the group, members of the attribute scope that are already on but are *not* part of the turn-on set receive those attributes and stay in their current on state — lights that are off stay off, and nothing flashes: the group issues at most two batched service calls computed from a single plan.

The group's `entity_id` attribute always lists the **base** members (like a regular group), so templates and `expand()` keep working as expected. Attributes `effective_power_on_members`, `effective_power_off_members`, `effective_attribute_members`, and `effective_state_members` show the sets currently in effect, along with the three toggle states and `last_applied_preset`.

### Companion switches

Every group device carries three switches — **Asymmetric power**, **Asymmetric attributes**, **Asymmetric state** — reflecting and controlling the toggles. Their starting values come from the defaults chosen at creation; flipping one takes effect immediately and survives restarts. This is how automations drive the group: e.g. an evening-mode automation turns on the *Asymmetric power* switch, and from then on the group turns on partially but turns off fully, until the switch is turned off again.

### Core group parity

- **Hide members** hides the base member entities (via the entity registry, exactly like a core group; members you hid yourself are never unhidden by the group).
- **All entities** applies to the effective *State* set: the group is on only when **all** state members are on.
- State computation otherwise mirrors core groups (any member on → group on, with the same `unknown`/`unavailable` rules), and reported brightness/colour are averaged over the currently-on attribute-scope members.

## Presets

Presets are named, reusable bundles of toggle states and member sets, stored in one **global library** shared by all Asymmetric Groups.

Presets are **sparse**: when a preset is applied, only the fields it actually contains are changed. A preset that stores only `asymmetric_power: true` flips that one toggle on every group it is applied to and leaves everything else alone — handy for applying a behaviour pattern (e.g. "evening mode") to many groups at once. A preset that also stores member lists acts more like a configuration clone for one specific group.

- **Save a snapshot:** call `asymmetric_group.save_preset` on a group to capture its full current runtime state as a preset. Refine it into a sparse pattern afterwards in the editor.
- **Edit the library:** open any Asymmetric Group's **Configure** dialog → **Preset library editor**. Pick an existing preset or create a new one; for each toggle choose *unchanged / on / off*, and for each member set tick *include* to store it.
- **Apply:** call `asymmetric_group.apply_preset`, or use the editor/services from automations. Applying sets the group's `last_applied_preset` attribute — a plain label of what was last applied; it does not attempt to detect later manual changes.
- **Delete:** `asymmetric_group.delete_preset`. Deleting a preset never changes groups that previously applied it (applying copies the values).

### Services

| Service | Fields | Description |
|---|---|---|
| `asymmetric_group.apply_preset` | `entity_id` (the group light), `preset` | Apply a preset to a group. Unknown preset names are an error. |
| `asymmetric_group.save_preset` | `entity_id`, `preset`, `overwrite` (default `false`) | Snapshot a group's runtime into the library. Fails if the name exists and `overwrite` is false. |
| `asymmetric_group.delete_preset` | `preset` | Remove a preset from the library. |

## Worked example

A bedroom has four lights: `light.bedroom_1` … `light.bedroom_4`.

Create an Asymmetric Group "Bedroom lights":

- Base members: all four.
- Power-ON members: `light.bedroom_3` only.
- Power-OFF members: all four.
- Attribute members: `light.bedroom_3`. State members: `light.bedroom_3`.
- Defaults: all three toggles **off** (the group starts life as a perfectly normal group).

An "evening / dim mode" automation turns on the group's three companion switches. Now:

- "Turn on the bedroom lights" → only `light.bedroom_3` lights.
- Someone manually turns on `light.bedroom_2` as well. The group still reads off-ish state from `light.bedroom_3` alone (State members), and the manually lit lamp does not make the group report a different brightness.
- A brightness change targets `light.bedroom_3` only.
- "Turn off the bedroom lights" → **all four** are switched off, including the manually lit `light.bedroom_2`.

When the mode ends, the automation turns the companion switches off and the group is an ordinary symmetric group again.

## Limitations

- **Only calls made on the group entity are affected.** Anything that bypasses the group — targeting an *area* or *label*, `light.turn_on` on individual members, scenes (which write member states directly), or another integration calling members itself — behaves exactly as it always did.
- **Light domain only in v1.** Switch groups may follow later.
- **No nested groups.** A member whose state carries an `entity_id` attribute (i.e. another group) is rejected in the creation flow.
- **Averaging simplification.** Reported colour mode is the unanimous mode of the currently-on attribute-scope members (falling back to the first on member's mode), rather than core groups' full capability negotiation.
- Toggling a dimension while an excluded light is on can change the group's reported on/off state without any light changing — the same trade-off any state-set definition implies.

## FAQ

**Is this a replacement for the built-in Group helper?**
No. It sits next to it. Use regular groups when symmetric behaviour is what you want; use an Asymmetric Group only where the asymmetry earns its keep.

**What happens on restart?**
Toggle states and (preset-modified) member sets are stored per group and restored. `last_applied_preset` is restored too.

**If I edit a group's member sets in Configure, what happens to runtime changes?**
Saving the member options re-seeds the runtime from the new configuration — runtime/preset modifications to that group are discarded by design, so the config page is always the ground truth after an edit.

**Can a preset break a group by referencing lights it doesn't have?**
No. Member lists from presets are filtered to the target group's base members when applied.

## License

MIT — see [LICENSE](LICENSE).
