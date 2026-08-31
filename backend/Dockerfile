# Multi-stage build for Go Hertz Backend API
FROM golang:1.23-alpine AS builder
WORKDIR /app

ENV GOTOOLCHAIN=local

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o screenscout-api main.go

# Production runtime stage
FROM alpine:3.19
WORKDIR /app

RUN apk add --no-cache ca-certificates tzdata curl
ENV TZ=Asia/Singapore

COPY --from=builder /app/screenscout-api .

EXPOSE 8080
CMD ["./screenscout-api"]
