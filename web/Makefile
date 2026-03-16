BINARY = aes-web
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
LDFLAGS = -ldflags="-s -w -X main.Version=$(VERSION)"

SSH_KEY ?= ~/.ssh/crypto_bot_ed25519
SSH_HOST ?= botuser@46.225.183.54
SSH_PORT ?= 2222
SSH_CMD = ssh -p $(SSH_PORT) -i $(SSH_KEY) -t $(SSH_HOST)
SCP_CMD = scp -P $(SSH_PORT) -i $(SSH_KEY)

.PHONY: build build-linux build-darwin test clean deploy deploy-static

build: build-linux

build-linux:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY) .

build-darwin:
	CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY)-darwin .

test:
	go test ./... -v -race

clean:
	rm -f $(BINARY) $(BINARY)-darwin

# Deploy static files only (templates, CSS) — no binary rebuild
deploy-static:
	$(SCP_CMD) templates/*.html $(SSH_HOST):/tmp/
	$(SCP_CMD) static/style.css $(SSH_HOST):/tmp/style.css
	$(SSH_CMD) 'sudo cp /tmp/*.html /var/lib/aes-web/templates/ && sudo cp /tmp/style.css /var/lib/aes-web/static/ && sudo systemctl restart aes-web'

# Full deploy — rebuild binary + static files
deploy: build-linux
	$(SCP_CMD) $(BINARY) $(SSH_HOST):/tmp/
	$(SCP_CMD) templates/*.html $(SSH_HOST):/tmp/
	$(SCP_CMD) static/style.css $(SSH_HOST):/tmp/style.css
	$(SSH_CMD) 'sudo systemctl stop aes-web && sudo cp /tmp/aes-web /usr/local/bin/ && sudo cp /tmp/*.html /var/lib/aes-web/templates/ && sudo cp /tmp/style.css /var/lib/aes-web/static/ && sudo systemctl start aes-web'
