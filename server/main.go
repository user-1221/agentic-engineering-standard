package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	switch os.Args[1] {
	case "serve":
		runServe()
	case "token":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Usage: aes-registry token <create|list|revoke>")
			os.Exit(1)
		}
		runToken(os.Args[2])
	case "version":
		fmt.Printf("aes-registry %s\n", Version)
	case "help", "--help", "-h":
		printUsage()
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n\n", os.Args[1])
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println(`aes-registry — AES Package Registry Server

Usage:
  aes-registry serve                 Start the registry server
  aes-registry token create --name N Create a new auth token
  aes-registry token list            List all tokens (names only)
  aes-registry token revoke --name N Revoke a token
  aes-registry version               Print version
  aes-registry help                  Print this help

Environment Variables:
  AES_REGISTRY_LISTEN          Bind address (default: 127.0.0.1:8080)
  AES_REGISTRY_DATA_DIR        Data directory (default: ./data)
  AES_REGISTRY_TOKENS_FILE     Tokens file path (default: ./tokens.json)
  AES_REGISTRY_AUDIT_LOG       Audit log path (default: ./audit.log)
  AES_REGISTRY_BACKUP_DIR      Index backup directory (default: ./backups)
  AES_REGISTRY_MAX_PACKAGE_SIZE Max tarball upload size in bytes (default: 52428800)
  AES_REGISTRY_MAX_INDEX_SIZE  Max index.json upload size in bytes (default: 5242880)
  AES_REGISTRY_LOG_LEVEL       Log level: debug, info, warn, error (default: info)`)
}

func runServe() {
	cfg := LoadConfig()

	// Initialize storage
	storage, err := NewStorage(cfg.DataDir, cfg.BackupDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to initialize storage: %v\n", err)
		os.Exit(1)
	}

	// Initialize token store
	tokens, err := NewTokenStore(cfg.TokensFile, cfg.AuditLog)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to initialize token store: %v\n", err)
		os.Exit(1)
	}

	// Initialize logger
	logger, err := NewLogger(cfg.LogLevel, cfg.AuditLog)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Close()

	// Initialize brute force limiter (5 failures per 15 minutes)
	bf := NewBruteForceLimiter(5, 15*time.Minute)

	// Create server and router
	srv := NewServer(storage, tokens, logger, bf, cfg)
	handler := srv.Router()

	httpServer := &http.Server{
		Addr:         cfg.ListenAddr,
		Handler:      handler,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 120 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// SIGHUP reloads tokens from disk (used by the web service after creating/revoking tokens)
	sighup := make(chan os.Signal, 1)
	signal.Notify(sighup, syscall.SIGHUP)
	go func() {
		for range sighup {
			if err := tokens.Reload(); err != nil {
				logger.Log("error", map[string]interface{}{
					"event": "token_reload_failed",
					"error": err.Error(),
				})
			} else {
				logger.Log("info", map[string]interface{}{
					"event": "tokens_reloaded",
				})
			}
		}
	}()

	// Graceful shutdown
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		logger.Log("info", map[string]interface{}{
			"event":   "server_start",
			"address": cfg.ListenAddr,
			"version": Version,
		})
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(1)
		}
	}()

	<-stop
	logger.Log("info", map[string]interface{}{"event": "server_shutdown"})

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	httpServer.Shutdown(ctx)
}

func runToken(subcmd string) {
	cfg := LoadConfig()
	tokens, err := NewTokenStore(cfg.TokensFile, "")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	switch subcmd {
	case "create":
		name := flagValue(os.Args[3:], "--name")
		if name == "" {
			fmt.Fprintln(os.Stderr, "Usage: aes-registry token create --name <name>")
			os.Exit(1)
		}
		raw, err := tokens.CreateToken(name)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(1)
		}
		fmt.Println("Token created. Save this — it will not be shown again:")
		fmt.Println()
		fmt.Printf("  export AES_REGISTRY_KEY=%s\n", raw)
		fmt.Println()

	case "list":
		entries := tokens.ListTokens()
		if len(entries) == 0 {
			fmt.Println("No tokens found.")
			return
		}
		fmt.Printf("%-20s %-24s %-24s %s\n", "NAME", "CREATED", "LAST USED", "PACKAGES")
		for _, e := range entries {
			lastUsed := e.LastUsed
			if lastUsed == "" {
				lastUsed = "never"
			}
			pkgs := "*"
			if len(e.AllowedPackages) > 0 {
				pkgs = fmt.Sprintf("%v", e.AllowedPackages)
			}
			fmt.Printf("%-20s %-24s %-24s %s\n", e.Name, e.CreatedAt, lastUsed, pkgs)
		}

	case "revoke":
		name := flagValue(os.Args[3:], "--name")
		if name == "" {
			fmt.Fprintln(os.Stderr, "Usage: aes-registry token revoke --name <name>")
			os.Exit(1)
		}
		if err := tokens.RevokeToken(name); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("Token %q revoked.\n", name)

	default:
		fmt.Fprintf(os.Stderr, "Unknown token command: %s\n", subcmd)
		fmt.Fprintln(os.Stderr, "Usage: aes-registry token <create|list|revoke>")
		os.Exit(1)
	}
}

// flagValue extracts a flag value from args. E.g., flagValue(["--name", "foo"], "--name") returns "foo".
func flagValue(args []string, flag string) string {
	for i, a := range args {
		if a == flag && i+1 < len(args) {
			return args[i+1]
		}
	}
	return ""
}
