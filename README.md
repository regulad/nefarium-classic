# nefarium

[![Project Status: Concept – Minimal or no implementation has been done yet, or the repository is only intended to be a limited example, demo, or proof-of-concept.](https://www.repostatus.org/badges/latest/concept.svg)](https://www.repostatus.org/#concept)
[![wakatime](https://wakatime.com/badge/github/regulad/nefarium.svg)](https://wakatime.com/badge/github/regulad/nefarium)

nefarium provides an API similar to OAuth for websites that do not support it.

## Installation

Docker is the preferred method of installation.

If you would not like to use Docker, you can install the package with poetry and run it in any shell.

```bash
poetry install . 
poetry run nefarium-start
```

## Configuration

### Configuring the backend

Use the [`docker-compose.yml`](./docker-compose.yml) to configure the nefarium backend on your server.

#### Environment Variables

| Variable Name                  | Description                                                                                                                                                                                                                                                                                                                         | Default                       |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| **`NEFARIUM_MONGO_DB`**        | The MongoDB database to use for data storage. This is also respected by the configuration CLI.                                                                                                                                                                                                                                      | `nefarium`                    |
| **`NEFARIUM_MONGO_URI`**       | The MongoDB database instance URI to connect to and use for data storage. This is respected by the configuration CLI, but manually passing a CLI argument will supercede this setting.                                                                                                                                              | `mongodb://localhost:27017`   |                                                                                
| **`NEFARIUM_DEBUG`**           | If the `DEBUG` log level should be used over `INFO`. Unneccisary in product, but could be handy during setup.                                                                                                                                                                                                                       | Unset (False)                 |
| **`NEFARIUM_PROXY`**           | Proxy to send requests data through. Should optimally be some rotating residential proxy like those provided by [Smartproxy](https://smartproxy.com), or one of your own creation. If a flow specifies a proxy, it will supercede this. <br/> *Due to a bug in authcaptureproxy, this may not always be used! Be careful of leaks!* | Attempts to read system proxy |
| **`NEFARIUM_DISCORD_WEBHOOK`** | A Discord webhook URL to send logging messages to using [`dislog`](https://github.com/regulad/dislog). ***Optional.***                                                                                                                                                                                                              | Unset                         |

### Adding login flows to your DB

Use the CLI included in the package.

```bash
poetry install .
poetry run nefarium --uri <MONGODB_URI> # this command will interactively guide you through the process of adding a login flow to the DB
```

## Integrating nefarium login flows into your app

### Native & noninteractive (i.e. headless) login

```python
from nefarium import client
```

### Interactive login

```js
// TODO
```

## Testing

```bash
poetry install . -D

poetry run tox  # Runs pytest
poetry run tox -e lint  # Runs linter
poetry run tox -e type  # Runs Type checker
```
