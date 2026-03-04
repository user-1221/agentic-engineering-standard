package main

import (
	"os"
	"strconv"
)

// Config holds all server configuration, loaded from environment variables.
type Config struct {
	ListenAddr      string
	DataDir         string
	TokensFile      string
	AuditLog        string
	BackupDir       string
	MaxPackageBytes int64
	MaxIndexBytes   int64
	LogLevel        string
}

func LoadConfig() Config {
	return Config{
		ListenAddr:      envOr("AES_REGISTRY_LISTEN", "127.0.0.1:8080"),
		DataDir:         envOr("AES_REGISTRY_DATA_DIR", "./data"),
		TokensFile:      envOr("AES_REGISTRY_TOKENS_FILE", "./tokens.json"),
		AuditLog:        envOr("AES_REGISTRY_AUDIT_LOG", "./audit.log"),
		BackupDir:       envOr("AES_REGISTRY_BACKUP_DIR", "./backups"),
		MaxPackageBytes: envOrInt64("AES_REGISTRY_MAX_PACKAGE_SIZE", 50*1024*1024),  // 50 MB
		MaxIndexBytes:   envOrInt64("AES_REGISTRY_MAX_INDEX_SIZE", 5*1024*1024),     // 5 MB
		LogLevel:        envOr("AES_REGISTRY_LOG_LEVEL", "info"),
	}
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envOrInt64(key string, fallback int64) int64 {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	n, err := strconv.ParseInt(v, 10, 64)
	if err != nil {
		return fallback
	}
	return n
}
