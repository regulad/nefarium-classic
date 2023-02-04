# nefarium

[![Project Status: Concept – Minimal or no implementation has been done yet, or the repository is only intended to be a limited example, demo, or proof-of-concept.](https://www.repostatus.org/badges/latest/concept.svg)](https://www.repostatus.org/#concept)
[![wakatime](https://wakatime.com/badge/github/regulad/nefarium.svg)](https://wakatime.com/badge/github/regulad/nefarium)

nefarium provides an API similar to OAuth for websites that do not support it.

Previously known as "the Me In The Middle auth backend" or "MeITM auth"

Inspired & powered by the following projects:

* [`authcaptureproxy`](https://pypi.org/project/authcaptureproxy/)
  * [`alexapy`](https://pypi.org/project/alexapy/)
  * [`alexa_media_player`](https://github.com/custom-components/alexa_media_player)
  * [Home Assistant](https://www.home-assistant.io)


## Installation

Docker is the preferred method of installation.

If you would not like to use Docker, you can install the package with poetry and run it in any shell.

```bash
poetry install . 
poetry run nefarium
```

## TODO

Highest priority first.

- [ ] Integration testing
- [ ] Easy flows for websites that don't support OAuth:
  - [x] Amazon (alexapy) (basically just translating an authcaptureproxy demo)
  - [ ] Twitter (should not be too hard) (funny, only dropped official API & OAuth support recently)
- [ ] Move from tox to pre-commit
- [ ] Public instance with Heroku
- [ ] CI/CD with GitHub Actions
- [ ] Bypass cloudflare challenges
- [ ] Tricky flows for websites that don't support OAuth:
  - [ ] TikTok (might be a bit tricky)
  - [ ] Discord (actually does support OAuth, but its scopes are extremely restrictive. we just need the user token) (stretch goal, will take a lot of work)
- [ ] Flow management endpoints

## Configuration

### Configuring the backend

Use the [`docker-compose.yml`](./docker-compose.yml) to configure the nefarium backend on your server.

#### Environment Variables

| Variable Name                  | Description                                                                                                                                                                                                                                                                                                                         | Default                       |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| **`NEFARIUM_HOST`**            | The host to bind the HTTP server to.                                                                                                                                                                                                                                                                                                | `0.0.0.0`                     |
| **`NEFARIUM_PORT`**            | The port for the HTTP server to listen to.                                                                                                                                                                                                                                                                                          | `8080`                        |
| **`NEFARIUM_MONGO_DB`**        | The MongoDB database to use for data storage. This is also respected by the configuration CLI.                                                                                                                                                                                                                                      | `nefarium`                    |
| **`NEFARIUM_MONGO_URI`**       | The MongoDB database instance URI to connect to and use for data storage. This is respected by the configuration CLI, but manually passing a CLI argument will supercede this setting.                                                                                                                                              | `mongodb://localhost:27017`   |                                                                                
| **`NEFARIUM_DEBUG`**           | If the `DEBUG` log level should be used over `INFO`. Unnecessary in production, but could be handy during setup.                                                                                                                                                                                                                    | Unset (False)                 |
| **`NEFARIUM_PROXY`**           | Proxy to send requests data through. Should optimally be some rotating residential proxy like those provided by [Smartproxy](https://smartproxy.com), or one of your own creation. If a flow specifies a proxy, it will supercede this. <br/> *Due to a bug in authcaptureproxy, this may not always be used! Be careful of leaks!* | Attempts to read system proxy |
| **`NEFARIUM_DISCORD_WEBHOOK`** | A Discord webhook URL to send logging messages to using [`dislog`](https://github.com/regulad/dislog). ***Optional.***                                                                                                                                                                                                              | Unset                         |
| **`NEFARIUM_REDIS_URI`**       | The Redis URI to use for caching.                                                                                                                                                                                                                                                                                                   | `redis://localhost:6379`      |

### Adding login flows to your DB

You'll need to add a flow to the database before you can use it. Some example flows (as JSON files) are stored in [./examples/flows](./examples/flows).

## Testing

```bash
poetry install . -D

poetry run tox  # Runs pytest
poetry run tox -e lint  # Runs linter
poetry run tox -e type  # Runs Type checker
```
