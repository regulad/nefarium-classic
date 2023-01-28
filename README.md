# nefarium

[![Project Status: Concept – Minimal or no implementation has been done yet, or the repository is only intended to be a limited example, demo, or proof-of-concept.](https://www.repostatus.org/badges/latest/concept.svg)](https://www.repostatus.org/#concept)
[![wakatime](https://wakatime.com/badge/github/regulad/nefarium.svg)](https://wakatime.com/badge/github/regulad/nefarium)

nefarium provides an API similar to OAuth for websites that do not support it.

## Installation

<!--TODO-->

## Configuration

### Configuring the backend

<!--TODO: Docker-->

### Adding login flows to your DB

Use the CLI included in the package.

```bash
poetry install .
poetry run nefarium --uri <MONGODB_URI> # this command will interactively guide you through the process of adding a login flow to the DB
```

## Integrating nefarium login flows into your app

<!--TODO-->

## Testing

```bash
poetry install . -D

poetry run tox  # Runs pytest
poetry run tox -e lint  # Runs linter
poetry run tox -e type  # Runs Type checker
```
