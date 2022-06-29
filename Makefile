COMPOSE:=docker compose
PI_DIR=pi

.PHONY=build build-api

build: build-api

build: CONTAINERS:=
build-api:
	$(COMPOSE) build --pull $(CONTAINERS)

up: CONTAINERS:=
up:
	$(COMPOSE) up --remove-orphans -d $(CONTAINERS)

CONTAINER:=api
shell:
	$(COMPOSE) run --rm --service-ports --use-aliases $(CONTAINER) bash

down:
	$(COMPOSE) down --remove-orphans
