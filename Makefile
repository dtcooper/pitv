COMPOSE:=docker compose
PI_DIR=pi

.PHONY=build build frontend up down shell

build: CONTAINERS:=
build:
	$(COMPOSE) build --pull $(CONTAINERS)

frontend:
	$(COMPOSE) build --pull frontend

up: CONTAINERS:=
up:
	$(COMPOSE) up --remove-orphans -d $(CONTAINERS)

shell: CONTAINER:=backend
shell:
	$(COMPOSE) run --rm --service-ports --use-aliases $(CONTAINER) bash || true

down:
	$(COMPOSE) down --remove-orphans
