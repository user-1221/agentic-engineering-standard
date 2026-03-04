BINARY = aes-registry
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
LDFLAGS = -ldflags="-s -w -X main.Version=$(VERSION)"

.PHONY: build build-linux build-darwin test clean

build: build-linux

build-linux:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY) .

build-darwin:
	CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY)-darwin .

test:
	go test ./... -v -race

clean:
	rm -f $(BINARY) $(BINARY)-darwin
