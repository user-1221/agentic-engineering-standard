package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestTokenCreateAndValidate(t *testing.T) {
	dir := t.TempDir()
	ts, err := NewTokenStore(filepath.Join(dir, "tokens.json"), "")
	if err != nil {
		t.Fatal(err)
	}

	// Create a token
	raw, err := ts.CreateToken("test")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(raw, tokenPrefix) {
		t.Errorf("token should start with %q, got %q", tokenPrefix, raw[:10])
	}

	// Validate with correct token
	entry, ok := ts.Validate(raw)
	if !ok {
		t.Error("valid token should be accepted")
	}
	if entry.Name != "test" {
		t.Errorf("token name should be 'test', got %q", entry.Name)
	}

	// Validate with wrong token
	_, ok = ts.Validate("wrong_token")
	if ok {
		t.Error("wrong token should be rejected")
	}
}

func TestTokenDuplicateName(t *testing.T) {
	dir := t.TempDir()
	ts, err := NewTokenStore(filepath.Join(dir, "tokens.json"), "")
	if err != nil {
		t.Fatal(err)
	}

	if _, err := ts.CreateToken("dup"); err != nil {
		t.Fatal(err)
	}
	if _, err := ts.CreateToken("dup"); err == nil {
		t.Error("duplicate name should be rejected")
	}
}

func TestTokenRevoke(t *testing.T) {
	dir := t.TempDir()
	ts, err := NewTokenStore(filepath.Join(dir, "tokens.json"), "")
	if err != nil {
		t.Fatal(err)
	}

	raw, _ := ts.CreateToken("revokeme")
	if err := ts.RevokeToken("revokeme"); err != nil {
		t.Fatal(err)
	}

	_, ok := ts.Validate(raw)
	if ok {
		t.Error("revoked token should be rejected")
	}
}

func TestTokenPersistence(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "tokens.json")

	ts1, _ := NewTokenStore(path, "")
	raw, _ := ts1.CreateToken("persist")

	// Reload from disk
	ts2, _ := NewTokenStore(path, "")
	_, ok := ts2.Validate(raw)
	if !ok {
		t.Error("token should persist across reloads")
	}
}

func TestTokenPackageAccess(t *testing.T) {
	entry := TokenEntry{
		AllowedPackages: []string{"train-*", "evaluate-*"},
	}

	ts := &TokenStore{}

	if !ts.CheckPackageAccess(&entry, "train-v2") {
		t.Error("train-v2 should match train-*")
	}
	if !ts.CheckPackageAccess(&entry, "evaluate-ml") {
		t.Error("evaluate-ml should match evaluate-*")
	}
	if ts.CheckPackageAccess(&entry, "deploy") {
		t.Error("deploy should not match restricted patterns")
	}

	// No restrictions
	openEntry := TokenEntry{}
	if !ts.CheckPackageAccess(&openEntry, "anything") {
		t.Error("empty allowed_packages should allow everything")
	}
}

func TestBruteForceLimiter(t *testing.T) {
	bf := NewBruteForceLimiter(3, 1*time.Second)

	// First 2 failures: not blocked
	if bf.RecordFailure("1.2.3.4") {
		t.Error("should not block after 1 failure")
	}
	if bf.RecordFailure("1.2.3.4") {
		t.Error("should not block after 2 failures")
	}
	// 3rd failure: blocked
	if !bf.RecordFailure("1.2.3.4") {
		t.Error("should block after 3 failures")
	}
	if !bf.IsBlocked("1.2.3.4") {
		t.Error("should report blocked")
	}

	// Different IP: not blocked
	if bf.IsBlocked("5.6.7.8") {
		t.Error("different IP should not be blocked")
	}
}

func TestTokensFileCreated(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "sub", "tokens.json")
	_, err := NewTokenStore(path, "")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(path); err != nil {
		t.Errorf("tokens file should be created: %v", err)
	}
}
