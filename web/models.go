package main

// User represents a registered user (from GitHub OAuth).
type User struct {
	ID          int64
	GitHubID    int64
	GitHubLogin string
	DisplayName string
	AvatarURL   string
	Email       string
	CreatedAt   string
	LastLogin   string
}

// Session maps a session token to a user.
type Session struct {
	Token     string
	UserID    int64
	CreatedAt string
	ExpiresAt string
}

// UserToken tracks ownership of registry tokens.
// The actual token hash lives in tokens.json (shared with the registry).
type UserToken struct {
	ID        int64
	UserID    int64
	TokenName string
	CreatedAt string
}
