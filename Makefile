COMPOSE:=docker compose
PI_DIR=pi

.PHONY=build build-api

build: build-api

build: CONTAINERS:=
build-api:
	$(COMPOSE) build $(CONTAINERS)

up: CONTAINERS:=
up:
	$(COMPOSE) up --remove-orphans $(shell source .env; if [ -z "$$DEBUG" -o "$$DEBUG" = 0 ]; then echo "-d"; fi) $(CONTAINERS)

CONTAINER:=api
shell:
	$(COMPOSE) run --rm --service-ports --use-aliases $(CONTAINER) bash

down:
	$(COMPOSE) down --remove-orphans
