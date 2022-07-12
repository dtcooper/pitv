COMPOSE:=docker compose
PI_DIR=pi

.PHONY: build frontend frontend-deploy up shell down

build: CONTAINERS:=
build:
	$(COMPOSE) build --pull $(CONTAINERS)

frontend:
	cd frontend && npm run build

frontend-deploy: frontend
	. .env && cd frontend/dist && rsync -aP --delete ./ "$$DEPLOY_SSH_TARGET"

up: CONTAINERS:=
up:
	$(COMPOSE) up --remove-orphans -d $(CONTAINERS)

shell: CONTAINER:=backend
shell:
	$(COMPOSE) run --rm --service-ports --use-aliases $(CONTAINER) bash || true

down:
	$(COMPOSE) down --remove-orphans
