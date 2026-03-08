package main

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"syscall"
	"time"
)

const tokenPrefix = "aes_tok_"

// tokenEntry matches the format in server/auth.go.
type tokenEntry struct {
	Hash      string   `json:"hash"`
	Name      string   `json:"name"`
	CreatedAt string   `json:"created_at"`
	LastUsed  string   `json:"last_used,omitempty"`
	Scopes    []string `json:"scopes"`
}

type tokensFile struct {
	Tokens []tokenEntry `json:"tokens"`
}

// TokenManager reads/writes the shared tokens.json file.
type TokenManager struct {
	path           string
	registryPIDFile string
}

func NewTokenManager(tokensPath, registryPIDFile string) *TokenManager {
	return &TokenManager{path: tokensPath, registryPIDFile: registryPIDFile}
}

// CreateToken generates a new registry token, writes it to tokens.json, and signals the registry.
// Returns the raw token (shown once to the user).
func (tm *TokenManager) CreateToken(name string) (string, error) {
	f, err := os.OpenFile(tm.path, os.O_RDWR|os.O_CREATE, 0660)
	if err != nil {
		return "", fmt.Errorf("open tokens file: %w", err)
	}
	defer f.Close()

	// Advisory file lock
	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX); err != nil {
		return "", fmt.Errorf("lock tokens file: %w", err)
	}
	defer syscall.Flock(int(f.Fd()), syscall.LOCK_UN)

	var tf tokensFile
	// Read from the locked fd instead of os.ReadFile to avoid TOCTOU
	if _, err := f.Seek(0, 0); err != nil {
		return "", fmt.Errorf("seek tokens file: %w", err)
	}
	data, err := io.ReadAll(f)
	if err != nil {
		return "", fmt.Errorf("read tokens file: %w", err)
	}
	if len(data) > 0 {
		if err := json.Unmarshal(data, &tf); err != nil {
			return "", fmt.Errorf("parse tokens file: %w", err)
		}
	}

	// Check for duplicate
	for _, t := range tf.Tokens {
		if t.Name == name {
			return "", fmt.Errorf("token with name %q already exists", name)
		}
	}

	// Generate token
	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", fmt.Errorf("generate random bytes: %w", err)
	}
	rawToken := tokenPrefix + hex.EncodeToString(raw)

	hash := sha256.Sum256([]byte(rawToken))
	entry := tokenEntry{
		Hash:      "sha256:" + hex.EncodeToString(hash[:]),
		Name:      name,
		CreatedAt: time.Now().UTC().Format(time.RFC3339),
		Scopes:    []string{"publish"},
	}
	tf.Tokens = append(tf.Tokens, entry)

	out, err := json.MarshalIndent(tf, "", "  ")
	if err != nil {
		return "", err
	}

	// Truncate and write
	if err := f.Truncate(0); err != nil {
		return "", err
	}
	if _, err := f.Seek(0, 0); err != nil {
		return "", err
	}
	if _, err := f.Write(append(out, '\n')); err != nil {
		return "", err
	}

	// Signal registry to reload
	tm.signalRegistry()

	return rawToken, nil
}

// RevokeToken removes a token from tokens.json by name.
func (tm *TokenManager) RevokeToken(name string) error {
	f, err := os.OpenFile(tm.path, os.O_RDWR, 0660)
	if err != nil {
		return fmt.Errorf("open tokens file: %w", err)
	}
	defer f.Close()

	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX); err != nil {
		return fmt.Errorf("lock tokens file: %w", err)
	}
	defer syscall.Flock(int(f.Fd()), syscall.LOCK_UN)

	// Read from the locked fd instead of os.ReadFile to avoid TOCTOU
	if _, err := f.Seek(0, 0); err != nil {
		return fmt.Errorf("seek tokens file: %w", err)
	}
	data, err := io.ReadAll(f)
	if err != nil {
		return fmt.Errorf("read tokens file: %w", err)
	}
	var tf tokensFile
	if err := json.Unmarshal(data, &tf); err != nil {
		return err
	}

	idx := -1
	for i, t := range tf.Tokens {
		if t.Name == name {
			idx = i
			break
		}
	}
	if idx == -1 {
		return fmt.Errorf("token %q not found in tokens.json", name)
	}

	tf.Tokens = append(tf.Tokens[:idx], tf.Tokens[idx+1:]...)

	out, err := json.MarshalIndent(tf, "", "  ")
	if err != nil {
		return err
	}

	if err := f.Truncate(0); err != nil {
		return err
	}
	if _, err := f.Seek(0, 0); err != nil {
		return err
	}
	if _, err := f.Write(append(out, '\n')); err != nil {
		return err
	}

	tm.signalRegistry()
	return nil
}

// signalRegistry is a no-op — the registry now watches tokens.json for
// changes via mtime polling, so no cross-process signal is needed.
func (tm *TokenManager) signalRegistry() {
	log.Printf("signalRegistry: tokens.json updated, registry will auto-reload within ~2s")
}
