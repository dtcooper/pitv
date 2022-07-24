COMPOSE:=docker compose
PI_DIR=pi

.PHONY: build frontend frontend-dev frontend-docker frontend-dev docker up shell down

build: CONTAINERS:=
build:
	$(COMPOSE) build --pull $(CONTAINERS)

frontend:
	cd frontend \
	&& if [ ! -d node_modules ]; then \
		npm install ; \
	fi \
	&& npm run build

frontend-dev:
	cd frontend \
	&& if [ ! -d node_modules ]; then \
		npm install ; \
	fi \
	&& npm run dev

frontend-docker:
	docker compose run --rm -e GIT_REV=$(shell git rev-parse HEAD) frontend sh -c '\
		if [ ! -d node_modules/ ]; then \
			npm install; \
		fi \
		&& npm run build'

frontend-dev-docker:
	docker compose run --rm --service-ports frontend sh -c '\
		if [ ! -d node_modules/ ]; then \
			npm install; \
		fi \
		&& npm run dev'

up: CONTAINERS:=
up:
	$(COMPOSE) up --remove-orphans -d $(CONTAINERS)

shell: CONTAINER:=backend
shell:
	$(COMPOSE) run --rm --service-ports --use-aliases $(CONTAINER) bash || true

down:
	$(COMPOSE) down --remove-orphans
