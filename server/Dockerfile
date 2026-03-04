FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /aes-registry .

FROM scratch
COPY --from=builder /aes-registry /aes-registry
VOLUME /data
EXPOSE 8080
ENTRYPOINT ["/aes-registry", "serve"]
