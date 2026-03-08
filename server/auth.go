package main

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const tokenPrefix = "aes_tok_"

// TokenEntry represents a stored auth token (hash only, never the raw token).
type TokenEntry struct {
	Hash            string   `json:"hash"`
	Name            string   `json:"name"`
	CreatedAt       string   `json:"created_at"`
	LastUsed        string   `json:"last_used,omitempty"`
	Scopes          []string `json:"scopes"`
	AllowedPackages []string `json:"allowed_packages,omitempty"`
}

// TokenStore manages auth tokens backed by a JSON file.
type TokenStore struct {
	mu       sync.RWMutex
	path     string
	tokens   []TokenEntry
	auditLog string
	lastMod  time.Time
}

// tokensFile is the on-disk format.
type tokensFile struct {
	Tokens []TokenEntry `json:"tokens"`
}

func NewTokenStore(path, auditLog string) (*TokenStore, error) {
	ts := &TokenStore{path: path, auditLog: auditLog}

	// Create file if it doesn't exist
	if _, err := os.Stat(path); os.IsNotExist(err) {
		if err := os.MkdirAll(filepath.Dir(path), 0750); err != nil {
			return nil, err
		}
		empty := tokensFile{Tokens: []TokenEntry{}}
		data, _ := json.MarshalIndent(empty, "", "  ")
		if err := os.WriteFile(path, data, 0600); err != nil {
			return nil, err
		}
	}

	if err := ts.load(); err != nil {
		return nil, fmt.Errorf("load tokens: %w", err)
	}

	// Record initial mtime for file watching
	if info, err := os.Stat(path); err == nil {
		ts.lastMod = info.ModTime()
	}

	return ts, nil
}

// Reload re-reads the tokens file from disk. Called on SIGHUP so that
// tokens created by the web service are picked up without restarting.
func (ts *TokenStore) Reload() error {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	return ts.load()
}

// WatchFile polls the tokens file for changes and reloads automatically.
// Call this in a goroutine. It runs until the context is cancelled.
func (ts *TokenStore) WatchFile(ctx context.Context, interval time.Duration, onReload func(error)) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			info, err := os.Stat(ts.path)
			if err != nil {
				continue
			}
			ts.mu.RLock()
			changed := info.ModTime().After(ts.lastMod)
			ts.mu.RUnlock()
			if changed {
				err := ts.Reload()
				ts.mu.Lock()
				ts.lastMod = info.ModTime()
				ts.mu.Unlock()
				if onReload != nil {
					onReload(err)
				}
			}
		}
	}
}

func (ts *TokenStore) load() error {
	data, err := os.ReadFile(ts.path)
	if err != nil {
		return err
	}
	var f tokensFile
	if err := json.Unmarshal(data, &f); err != nil {
		return err
	}
	ts.tokens = f.Tokens
	return nil
}

func (ts *TokenStore) save() error {
	f := tokensFile{Tokens: ts.tokens}
	data, err := json.MarshalIndent(f, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(ts.path, append(data, '\n'), 0600)
}

// CreateToken generates a new token, stores the hash, and returns the raw token.
// The raw token is only returned once and never stored.
func (ts *TokenStore) CreateToken(name string) (string, error) {
	ts.mu.Lock()
	defer ts.mu.Unlock()

	// Check for duplicate name
	for _, t := range ts.tokens {
		if t.Name == name {
			return "", fmt.Errorf("token with name %q already exists", name)
		}
	}

	// Generate 32 random bytes
	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", fmt.Errorf("generate random bytes: %w", err)
	}
	rawToken := tokenPrefix + hex.EncodeToString(raw)

	// Store only the hash
	hash := hashToken(rawToken)
	entry := TokenEntry{
		Hash:      "sha256:" + hash,
		Name:      name,
		CreatedAt: time.Now().UTC().Format(time.RFC3339),
		Scopes:    []string{"publish"},
	}
	ts.tokens = append(ts.tokens, entry)

	if err := ts.save(); err != nil {
		return "", err
	}
	return rawToken, nil
}

// ListTokens returns token metadata (never raw tokens).
func (ts *TokenStore) ListTokens() []TokenEntry {
	ts.mu.RLock()
	defer ts.mu.RUnlock()
	result := make([]TokenEntry, len(ts.tokens))
	copy(result, ts.tokens)
	return result
}

// RevokeToken removes a token by name.
func (ts *TokenStore) RevokeToken(name string) error {
	ts.mu.Lock()
	defer ts.mu.Unlock()

	idx := -1
	for i, t := range ts.tokens {
		if t.Name == name {
			idx = i
			break
		}
	}
	if idx == -1 {
		return fmt.Errorf("token %q not found", name)
	}

	ts.tokens = append(ts.tokens[:idx], ts.tokens[idx+1:]...)
	return ts.save()
}

// Validate checks a raw bearer token against stored hashes.
// Returns a copy of the matching TokenEntry and true if valid.
func (ts *TokenStore) Validate(rawToken string) (TokenEntry, bool) {
	ts.mu.RLock()
	defer ts.mu.RUnlock()

	hash := hashToken(rawToken)
	for i := range ts.tokens {
		storedHash := strings.TrimPrefix(ts.tokens[i].Hash, "sha256:")
		if constantTimeEqual(hash, storedHash) {
			// Copy before releasing lock to avoid data race
			entry := ts.tokens[i]
			name := entry.Name
			// Update last_used (best effort, don't fail the request)
			go ts.updateLastUsed(name)
			return entry, true
		}
	}
	return TokenEntry{}, false
}

// CheckPackageAccess verifies the token is allowed to publish to this package name.
func (ts *TokenStore) CheckPackageAccess(entry *TokenEntry, packageName string) bool {
	if len(entry.AllowedPackages) == 0 {
		return true // no restrictions
	}
	for _, pattern := range entry.AllowedPackages {
		if matchGlob(pattern, packageName) {
			return true
		}
	}
	return false
}

func (ts *TokenStore) updateLastUsed(name string) {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	for i := range ts.tokens {
		if ts.tokens[i].Name == name {
			ts.tokens[i].LastUsed = time.Now().UTC().Format(time.RFC3339)
			_ = ts.save()
			return
		}
	}
}

func hashToken(raw string) string {
	h := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(h[:])
}

func constantTimeEqual(a, b string) bool {
	return subtle.ConstantTimeCompare([]byte(a), []byte(b)) == 1
}

// matchGlob does simple glob matching with * wildcard.
func matchGlob(pattern, s string) bool {
	if pattern == "*" {
		return true
	}
	if strings.HasSuffix(pattern, "*") {
		return strings.HasPrefix(s, pattern[:len(pattern)-1])
	}
	if strings.HasPrefix(pattern, "*") {
		return strings.HasSuffix(s, pattern[1:])
	}
	return pattern == s
}

// BruteForceLimiter tracks auth failures per IP to prevent brute force attacks.
type BruteForceLimiter struct {
	mu       sync.Mutex
	failures map[string]*failureRecord
	maxFails int
	window   time.Duration
}

type failureRecord struct {
	count    int
	firstAt  time.Time
	blockedUntil time.Time
}

func NewBruteForceLimiter(maxFails int, window time.Duration) *BruteForceLimiter {
	bf := &BruteForceLimiter{
		failures: make(map[string]*failureRecord),
		maxFails: maxFails,
		window:   window,
	}
	go bf.cleanup()
	return bf
}

// RecordFailure records an auth failure for an IP. Returns true if the IP is now blocked.
func (bf *BruteForceLimiter) RecordFailure(ip string) bool {
	bf.mu.Lock()
	defer bf.mu.Unlock()

	now := time.Now()
	rec, ok := bf.failures[ip]
	if !ok || now.After(rec.firstAt.Add(bf.window)) {
		bf.failures[ip] = &failureRecord{count: 1, firstAt: now}
		return false
	}

	rec.count++
	if rec.count >= bf.maxFails {
		rec.blockedUntil = now.Add(bf.window)
		return true
	}
	return false
}

// IsBlocked checks if an IP is currently blocked.
func (bf *BruteForceLimiter) IsBlocked(ip string) bool {
	bf.mu.Lock()
	defer bf.mu.Unlock()

	rec, ok := bf.failures[ip]
	if !ok {
		return false
	}
	if time.Now().Before(rec.blockedUntil) {
		return true
	}
	return false
}

func (bf *BruteForceLimiter) cleanup() {
	for {
		time.Sleep(5 * time.Minute)
		bf.mu.Lock()
		now := time.Now()
		for ip, rec := range bf.failures {
			if now.After(rec.firstAt.Add(bf.window)) && now.After(rec.blockedUntil) {
				delete(bf.failures, ip)
			}
		}
		bf.mu.Unlock()
	}
}
