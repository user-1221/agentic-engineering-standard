package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

var Version = "dev"

func main() {
	cfg := LoadConfig()

	if cfg.SessionSecret == "" {
		fmt.Fprintln(os.Stderr, "Error: AES_WEB_SESSION_SECRET is required")
		os.Exit(1)
	}
	if cfg.GitHubClientID == "" || cfg.GitHubClientSecret == "" {
		fmt.Fprintln(os.Stderr, "Error: AES_WEB_GITHUB_CLIENT_ID and AES_WEB_GITHUB_CLIENT_SECRET are required")
		os.Exit(1)
	}

	// Open database
	db, err := OpenDB(cfg.DBPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to open database: %v\n", err)
		os.Exit(1)
	}
	defer db.Close()

	// GitHub OAuth
	oauth := &GitHubOAuth{
		ClientID:     cfg.GitHubClientID,
		ClientSecret: cfg.GitHubClientSecret,
		RedirectURI:  cfg.BaseURL + "/auth/github/callback",
	}

	// Token manager (shared tokens.json)
	tokens := NewTokenManager(cfg.TokensFile, cfg.RegistryPIDFile)

	// App
	app, err := NewApp(db, oauth, tokens, cfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	httpServer := &http.Server{
		Addr:         cfg.ListenAddr,
		Handler:      app.Router(),
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Session cleanup goroutine
	go func() {
		for {
			time.Sleep(1 * time.Hour)
			if err := db.CleanExpiredSessions(); err != nil {
				log.Printf("session cleanup error: %v", err)
			}
		}
	}()

	// Graceful shutdown
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("aes-web %s listening on %s", Version, cfg.ListenAddr)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(1)
		}
	}()

	<-stop
	log.Println("shutting down...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	httpServer.Shutdown(ctx)
}
