package main

import "os"

// Config holds all configuration for the web service.
type Config struct {
	ListenAddr         string
	DBPath             string
	TokensFile         string
	RegistryPIDFile    string
	SessionSecret      string
	GitHubClientID     string
	GitHubClientSecret string
	BaseURL            string
	DocsURL            string
	RegistryURL        string
	MaxTokensPerUser   int
}

func LoadConfig() Config {
	return Config{
		ListenAddr:         envOr("AES_WEB_LISTEN", "127.0.0.1:8081"),
		DBPath:             envOr("AES_WEB_DB", "./aes-web.db"),
		TokensFile:         envOr("AES_WEB_TOKENS_FILE", "./tokens.json"),
		RegistryPIDFile:    envOr("AES_WEB_REGISTRY_PID_FILE", ""),
		SessionSecret:      envOr("AES_WEB_SESSION_SECRET", ""),
		GitHubClientID:     envOr("AES_WEB_GITHUB_CLIENT_ID", ""),
		GitHubClientSecret: envOr("AES_WEB_GITHUB_CLIENT_SECRET", ""),
		BaseURL:            envOr("AES_WEB_BASE_URL", "http://localhost:8081"),
		DocsURL:            envOr("AES_WEB_DOCS_URL", "https://github.com/user-1221/agentic-engineering-standard"),
		RegistryURL:        envOr("AES_WEB_REGISTRY_URL", "https://registry.aes-official.com"),
		MaxTokensPerUser:   10,
	}
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
