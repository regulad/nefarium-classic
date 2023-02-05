# nefarium

[![Project Status: WIP – Initial development is in progress, but there has not yet been a stable, usable release suitable for the public.](https://www.repostatus.org/badges/latest/wip.svg)](https://www.repostatus.org/#wip)
[![wakatime](https://wakatime.com/badge/github/regulad/nefarium.svg)](https://wakatime.com/badge/github/regulad/nefarium)
[![CI status](https://github.com/nefarium/nefarium/actions/workflows/ci.yml/badge.svg)](https://github.com/nefarium/nefarium/actions/workflows/ci.yml)
[![Docker status](https://github.com/nefarium/nefarium/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/nefarium/nefarium/actions/workflows/docker-publish.yml)
[![Discord](https://img.shields.io/discord/1071033007663751179?logo=discord)](https://discord.gg/vPvcNb9RNx)

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
poetry install --only main
poetry run nefarium
```

## TODO

Highest priority first.

- [ ] Integration testing
- [ ] Easy flows for websites that don't support OAuth:
  - [x] Amazon (alexapy) (basically just translating an authcaptureproxy demo)
  - [ ] Twitter (should not be too hard) (funny, only dropped official API & OAuth support recently)
- [x] Setup pre-commit
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

## Contributing

### Setup

First, install the dependencies:

```bash
poetry install --no-root
```

Second, install the pre-commit hooks:

```bash
pre-commit install
```

Now, you are ready to start contributing! Please fork the repository and make a pull request with your changes.

### Testing

To run the tests, use the following command:

```bash
poetry run tox
```

This will run everything, including linters, tests, typing tests, and coverage.
