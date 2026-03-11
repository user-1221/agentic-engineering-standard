package main

import (
	"path/filepath"
	"testing"
	"time"
)

func setupTestDB(t *testing.T) *DB {
	t.Helper()
	db, err := OpenDB(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return db
}

func TestOpenDB(t *testing.T) {
	db := setupTestDB(t)
	if db == nil {
		t.Fatal("expected non-nil DB")
	}
}

func TestOpenDB_InvalidPath(t *testing.T) {
	_, err := OpenDB("/nonexistent/path/test.db")
	if err == nil {
		t.Error("expected error for invalid path")
	}
}

func TestUpsertUser_Create(t *testing.T) {
	db := setupTestDB(t)
	user, err := db.UpsertUser(12345, "testuser", "Test User", "https://avatar.example.com/1.png", "test@example.com")
	if err != nil {
		t.Fatal(err)
	}
	if user.GitHubID != 12345 {
		t.Errorf("github_id: got %d, want 12345", user.GitHubID)
	}
	if user.GitHubLogin != "testuser" {
		t.Errorf("github_login: got %q, want %q", user.GitHubLogin, "testuser")
	}
	if user.DisplayName != "Test User" {
		t.Errorf("display_name: got %q, want %q", user.DisplayName, "Test User")
	}
	if user.AvatarURL != "https://avatar.example.com/1.png" {
		t.Errorf("avatar_url: got %q", user.AvatarURL)
	}
}

func TestUpsertUser_Update(t *testing.T) {
	db := setupTestDB(t)

	// Create
	_, err := db.UpsertUser(12345, "testuser", "Test User", "", "")
	if err != nil {
		t.Fatal(err)
	}

	// Update (same github_id, different display name)
	user, err := db.UpsertUser(12345, "testuser", "Updated Name", "https://new-avatar.png", "new@example.com")
	if err != nil {
		t.Fatal(err)
	}
	if user.DisplayName != "Updated Name" {
		t.Errorf("display_name after update: got %q, want %q", user.DisplayName, "Updated Name")
	}
	if user.Email != "new@example.com" {
		t.Errorf("email after update: got %q, want %q", user.Email, "new@example.com")
	}
}

func TestGetUserByGitHubID_NotFound(t *testing.T) {
	db := setupTestDB(t)
	user, err := db.GetUserByGitHubID(99999)
	if err != nil {
		t.Fatal(err)
	}
	if user != nil {
		t.Error("expected nil user for non-existent github_id")
	}
}

func TestGetUserByID_NotFound(t *testing.T) {
	db := setupTestDB(t)
	user, err := db.GetUserByID(99999)
	if err != nil {
		t.Fatal(err)
	}
	if user != nil {
		t.Error("expected nil user for non-existent id")
	}
}

func TestCreateSession(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")

	token, err := db.CreateSession(user.ID)
	if err != nil {
		t.Fatal(err)
	}
	if token == "" {
		t.Error("expected non-empty session token")
	}
	if len(token) != 64 { // 32 bytes hex-encoded
		t.Errorf("session token length: got %d, want 64", len(token))
	}
}

func TestGetSession_Valid(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")
	token, _ := db.CreateSession(user.ID)

	got, err := db.GetSession(token)
	if err != nil {
		t.Fatal(err)
	}
	if got == nil {
		t.Fatal("expected non-nil user from valid session")
	}
	if got.ID != user.ID {
		t.Errorf("session user id: got %d, want %d", got.ID, user.ID)
	}
}

func TestGetSession_InvalidToken(t *testing.T) {
	db := setupTestDB(t)
	user, err := db.GetSession("nonexistent-token")
	if err != nil {
		t.Fatal(err)
	}
	if user != nil {
		t.Error("expected nil user for invalid session token")
	}
}

func TestDeleteSession(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")
	token, _ := db.CreateSession(user.ID)

	if err := db.DeleteSession(token); err != nil {
		t.Fatal(err)
	}

	got, err := db.GetSession(token)
	if err != nil {
		t.Fatal(err)
	}
	if got != nil {
		t.Error("expected nil user after session deletion")
	}
}

func TestCleanExpiredSessions(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")

	// Insert an already-expired session directly
	expired := time.Now().UTC().Add(-1 * time.Hour).Format(time.RFC3339)
	db.db.Exec(`INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)`,
		"expired-token", user.ID, expired)

	// Also create a valid session
	validToken, _ := db.CreateSession(user.ID)

	if err := db.CleanExpiredSessions(); err != nil {
		t.Fatal(err)
	}

	// Expired session should be gone
	got, _ := db.GetSession("expired-token")
	if got != nil {
		t.Error("expired session should have been cleaned")
	}

	// Valid session should remain
	got, _ = db.GetSession(validToken)
	if got == nil {
		t.Error("valid session should not have been cleaned")
	}
}

func TestCreateUserToken(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")

	if err := db.CreateUserToken(user.ID, "testuser-mytoken"); err != nil {
		t.Fatal(err)
	}

	tokens, err := db.ListUserTokens(user.ID)
	if err != nil {
		t.Fatal(err)
	}
	if len(tokens) != 1 {
		t.Fatalf("token count: got %d, want 1", len(tokens))
	}
	if tokens[0].TokenName != "testuser-mytoken" {
		t.Errorf("token name: got %q, want %q", tokens[0].TokenName, "testuser-mytoken")
	}
}

func TestCreateUserToken_Duplicate(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")

	db.CreateUserToken(user.ID, "testuser-mytoken")
	err := db.CreateUserToken(user.ID, "testuser-mytoken")
	if err == nil {
		t.Error("expected error for duplicate token name")
	}
}

func TestCountUserTokens(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")

	count, err := db.CountUserTokens(user.ID)
	if err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Errorf("initial count: got %d, want 0", count)
	}

	db.CreateUserToken(user.ID, "token1")
	db.CreateUserToken(user.ID, "token2")

	count, _ = db.CountUserTokens(user.ID)
	if count != 2 {
		t.Errorf("after 2 tokens: got %d, want 2", count)
	}
}

func TestDeleteUserToken(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")
	db.CreateUserToken(user.ID, "testuser-mytoken")

	if err := db.DeleteUserToken(user.ID, "testuser-mytoken"); err != nil {
		t.Fatal(err)
	}

	tokens, _ := db.ListUserTokens(user.ID)
	if len(tokens) != 0 {
		t.Errorf("token count after delete: got %d, want 0", len(tokens))
	}
}

func TestDeleteUserToken_NotFound(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")

	err := db.DeleteUserToken(user.ID, "nonexistent")
	if err == nil {
		t.Error("expected error deleting non-existent token")
	}
}

func TestDeleteUserToken_WrongOwner(t *testing.T) {
	db := setupTestDB(t)
	user1, _ := db.UpsertUser(11111, "user1", "User 1", "", "")
	user2, _ := db.UpsertUser(22222, "user2", "User 2", "", "")

	db.CreateUserToken(user1.ID, "user1-token")

	err := db.DeleteUserToken(user2.ID, "user1-token")
	if err == nil {
		t.Error("expected error when wrong user tries to delete token")
	}

	// Token should still exist for user1
	tokens, _ := db.ListUserTokens(user1.ID)
	if len(tokens) != 1 {
		t.Error("token should not have been deleted by wrong owner")
	}
}

func TestListUserTokens_ReturnsAll(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")

	db.CreateUserToken(user.ID, "first")
	db.CreateUserToken(user.ID, "second")
	db.CreateUserToken(user.ID, "third")

	tokens, _ := db.ListUserTokens(user.ID)
	if len(tokens) != 3 {
		t.Fatalf("token count: got %d, want 3", len(tokens))
	}

	names := map[string]bool{}
	for _, tok := range tokens {
		names[tok.TokenName] = true
	}
	for _, want := range []string{"first", "second", "third"} {
		if !names[want] {
			t.Errorf("missing token %q", want)
		}
	}
}
