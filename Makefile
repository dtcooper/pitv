COMPOSE:=docker compose
SHELL=/bin/bash
CONTAINERS:=
CONTAINER:=app

.PHONY: build
build:
	$(COMPOSE) build --pull player

.PHONY: shell
shell:
	$(COMPOSE) run --rm --service-ports --use-aliases player bash || true
