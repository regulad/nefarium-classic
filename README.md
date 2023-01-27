# nefarium

nefarium provides an API similar to OAuth for websites that do not support it.

## Installation

<!--TODO-->

## Configuration

### Configuring the backend

<!--TODO-->

### Adding login flows to your DB

Use the CLI included in the package.

```bash
nefarium connect  # this command will interactively allow you to enter MongoDB connection information and saves it to ~/.nefarium as a TOML file
nefarium insert  # this command will interactively guide you through the process of adding a login flow to the DB
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
