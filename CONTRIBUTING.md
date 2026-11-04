# Contributing

Thanks for helping improve Asymmetric Group!

## Ground rules

- **Bugs and ideas first:** open an issue before a large pull request so the
  approach can be agreed before you invest the work.
- **Keep the domain model intact:** base members are the full set; power,
  attributes, and state subgroups are always filtered to the base set, and
  applying attributes must never turn a light on. Changes that break those
  invariants need a design discussion in an issue first.
- **Storage and service compatibility matter:** the domain
  (`asymmetric_group`), service names, storage keys, and entity unique-id
  scheme are load-bearing for existing installs — do not rename them.

## Development

The member-set logic lives in `custom_components/asymmetric_group/engine.py`
and is deliberately free of Home Assistant imports, so it can be unit-tested
with the standard library alone:

```bash
python -m unittest discover -s tests
```

Home Assistant level tests (config flow, light platform) are not in the
repo yet — they are planned on top of
[pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component).
Until they land, cover member-set behaviour in the engine tests and verify
flow changes in a dev Home Assistant instance.

CI (`.github/workflows/validate.yaml`) runs the unit tests, the HACS
action, and hassfest on every push — please make sure your change keeps
all three green.

## Pull requests

- One topic per PR, with tests for behaviour changes.
- Update the README when behaviour, services, or setup steps change.
- Describe user-visible changes in the PR body; releases are cut from tags
  whose version matches `manifest.json`.
