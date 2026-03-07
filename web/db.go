package main

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

// DB wraps SQLite operations.
type DB struct {
	db *sql.DB
}

func OpenDB(path string) (*DB, error) {
	db, err := sql.Open("sqlite", path+"?_pragma=journal_mode(wal)&_pragma=busy_timeout(5000)")
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	d := &DB{db: db}
	if err := d.migrate(); err != nil {
		return nil, fmt.Errorf("migrate: %w", err)
	}
	return d, nil
}

func (d *DB) Close() error {
	return d.db.Close()
}

func (d *DB) migrate() error {
	_, err := d.db.Exec(`
		CREATE TABLE IF NOT EXISTS users (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			github_id    INTEGER UNIQUE NOT NULL,
			github_login TEXT NOT NULL,
			display_name TEXT NOT NULL,
			avatar_url   TEXT DEFAULT '',
			email        TEXT DEFAULT '',
			created_at   TEXT NOT NULL DEFAULT (datetime('now')),
			last_login   TEXT NOT NULL DEFAULT (datetime('now'))
		);

		CREATE TABLE IF NOT EXISTS sessions (
			token      TEXT PRIMARY KEY,
			user_id    INTEGER NOT NULL REFERENCES users(id),
			created_at TEXT NOT NULL DEFAULT (datetime('now')),
			expires_at TEXT NOT NULL
		);

		CREATE TABLE IF NOT EXISTS user_tokens (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			user_id    INTEGER NOT NULL REFERENCES users(id),
			token_name TEXT NOT NULL,
			created_at TEXT NOT NULL DEFAULT (datetime('now')),
			UNIQUE(user_id, token_name)
		);
	`)
	return err
}

// UpsertUser creates or updates a user from GitHub OAuth data.
func (d *DB) UpsertUser(githubID int64, login, displayName, avatarURL, email string) (*User, error) {
	now := time.Now().UTC().Format(time.RFC3339)
	_, err := d.db.Exec(`
		INSERT INTO users (github_id, github_login, display_name, avatar_url, email, created_at, last_login)
		VALUES (?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(github_id) DO UPDATE SET
			github_login = excluded.github_login,
			display_name = excluded.display_name,
			avatar_url   = excluded.avatar_url,
			email        = excluded.email,
			last_login   = excluded.last_login
	`, githubID, login, displayName, avatarURL, email, now, now)
	if err != nil {
		return nil, err
	}
	return d.GetUserByGitHubID(githubID)
}

func (d *DB) GetUserByGitHubID(githubID int64) (*User, error) {
	u := &User{}
	err := d.db.QueryRow(`
		SELECT id, github_id, github_login, display_name, avatar_url, email, created_at, last_login
		FROM users WHERE github_id = ?
	`, githubID).Scan(&u.ID, &u.GitHubID, &u.GitHubLogin, &u.DisplayName, &u.AvatarURL, &u.Email, &u.CreatedAt, &u.LastLogin)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	return u, err
}

func (d *DB) GetUserByID(id int64) (*User, error) {
	u := &User{}
	err := d.db.QueryRow(`
		SELECT id, github_id, github_login, display_name, avatar_url, email, created_at, last_login
		FROM users WHERE id = ?
	`, id).Scan(&u.ID, &u.GitHubID, &u.GitHubLogin, &u.DisplayName, &u.AvatarURL, &u.Email, &u.CreatedAt, &u.LastLogin)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	return u, err
}

// CreateSession creates a new session for a user (7-day expiry).
func (d *DB) CreateSession(userID int64) (string, error) {
	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", err
	}
	token := hex.EncodeToString(raw)
	expiresAt := time.Now().UTC().Add(7 * 24 * time.Hour).Format(time.RFC3339)
	_, err := d.db.Exec(`INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)`,
		token, userID, expiresAt)
	return token, err
}

// GetSession returns the user for a valid (non-expired) session token.
func (d *DB) GetSession(token string) (*User, error) {
	var userID int64
	var expiresAt string
	err := d.db.QueryRow(`SELECT user_id, expires_at FROM sessions WHERE token = ?`, token).Scan(&userID, &expiresAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	exp, err := time.Parse(time.RFC3339, expiresAt)
	if err != nil || time.Now().UTC().After(exp) {
		d.db.Exec(`DELETE FROM sessions WHERE token = ?`, token)
		return nil, nil
	}
	return d.GetUserByID(userID)
}

func (d *DB) DeleteSession(token string) error {
	_, err := d.db.Exec(`DELETE FROM sessions WHERE token = ?`, token)
	return err
}

// CreateUserToken records that a user owns a token name.
func (d *DB) CreateUserToken(userID int64, tokenName string) error {
	_, err := d.db.Exec(`INSERT INTO user_tokens (user_id, token_name) VALUES (?, ?)`, userID, tokenName)
	return err
}

// ListUserTokens returns all token names owned by a user.
func (d *DB) ListUserTokens(userID int64) ([]UserToken, error) {
	rows, err := d.db.Query(`SELECT id, user_id, token_name, created_at FROM user_tokens WHERE user_id = ? ORDER BY created_at DESC`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var tokens []UserToken
	for rows.Next() {
		var t UserToken
		if err := rows.Scan(&t.ID, &t.UserID, &t.TokenName, &t.CreatedAt); err != nil {
			return nil, err
		}
		tokens = append(tokens, t)
	}
	return tokens, rows.Err()
}

// CountUserTokens returns the number of tokens a user owns.
func (d *DB) CountUserTokens(userID int64) (int, error) {
	var count int
	err := d.db.QueryRow(`SELECT COUNT(*) FROM user_tokens WHERE user_id = ?`, userID).Scan(&count)
	return count, err
}

// DeleteUserToken removes a token ownership record.
func (d *DB) DeleteUserToken(userID int64, tokenName string) error {
	result, err := d.db.Exec(`DELETE FROM user_tokens WHERE user_id = ? AND token_name = ?`, userID, tokenName)
	if err != nil {
		return err
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return fmt.Errorf("token %q not found", tokenName)
	}
	return nil
}

// CleanExpiredSessions removes expired sessions.
func (d *DB) CleanExpiredSessions() error {
	_, err := d.db.Exec(`DELETE FROM sessions WHERE expires_at < datetime('now')`)
	return err
}
