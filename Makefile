COMPOSE:=docker compose
PI_DIR=pi

.PHONY: build frontend up shell down

build: CONTAINERS:=
build:
	$(COMPOSE) build --pull $(CONTAINERS)

frontend:
	cd frontend \
	&& if [ ! -d node_modules ]; then \
		npm install ; \
	fi \
	&& npm run build

frontend-docker:
	docker compose run --rm frontend sh -c '\
		if [ ! -d node_modules/ ]; then \
			npm install; \
		fi \
		&& npm run build'

up: CONTAINERS:=
up:
	$(COMPOSE) up --remove-orphans -d $(CONTAINERS)

shell: CONTAINER:=backend
shell:
	$(COMPOSE) run --rm --service-ports --use-aliases $(CONTAINER) bash || true

down:
	$(COMPOSE) down --remove-orphans
