package main

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

// App holds shared dependencies for all handlers.
type App struct {
	DB        *DB
	OAuth     *GitHubOAuth
	Tokens    *TokenManager
	Config    Config
	Templates *template.Template
}

// isSecure returns true if the app is configured with an HTTPS base URL.
func (a *App) isSecure() bool {
	return strings.HasPrefix(a.Config.BaseURL, "https://")
}

func NewApp(db *DB, oauth *GitHubOAuth, tokens *TokenManager, cfg Config) (*App, error) {
	tmpl, err := template.ParseGlob(filepath.Join("templates", "*.html"))
	if err != nil {
		return nil, fmt.Errorf("parse templates: %w", err)
	}
	return &App{
		DB:        db,
		OAuth:     oauth,
		Tokens:    tokens,
		Config:    cfg,
		Templates: tmpl,
	}, nil
}

func (a *App) Router() http.Handler {
	mux := http.NewServeMux()

	// Rate limiter for sensitive endpoints (10 req/min per IP)
	sensitiveRL := newWebRateLimiter(10, time.Minute)

	// Static files
	mux.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("static"))))

	// Public routes
	mux.HandleFunc("/", a.handleIndex)
	mux.HandleFunc("/login", a.handleLogin)
	mux.HandleFunc("/auth/github/callback", rateLimitHandler(sensitiveRL, a.handleGitHubCallback))
	mux.HandleFunc("/docs", a.handleDocs)

	// Authenticated routes
	mux.HandleFunc("/dashboard", requireAuth(a.handleDashboard))
	mux.HandleFunc("/dashboard/tokens/new", requireAuth(rateLimitHandler(sensitiveRL, a.handleTokenCreate)))
	mux.HandleFunc("/dashboard/tokens/revoke", requireAuth(rateLimitHandler(sensitiveRL, a.handleTokenRevoke)))
	mux.HandleFunc("/logout", requireAuth(a.handleLogout))

	// Middleware chain: logging → security headers → CSRF → session auth
	return requestLogger(webSecurityHeaders(csrfProtect(a.isSecure(), sessionAuth(a.DB, mux))))
}

func (a *App) handleIndex(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	user := userFromCtx(r)
	a.render(w, "index.html", map[string]interface{}{
		"User": user,
	})
}

func (a *App) handleLogin(w http.ResponseWriter, r *http.Request) {
	// Generate state parameter
	raw := make([]byte, 32)
	rand.Read(raw)
	state := hex.EncodeToString(raw)

	http.SetCookie(w, &http.Cookie{
		Name:     "oauth_state",
		Value:    state,
		Path:     "/",
		HttpOnly: true,
		Secure:   a.isSecure(),
		SameSite: http.SameSiteLaxMode,
		MaxAge:   600, // 10 minutes
	})

	http.Redirect(w, r, a.OAuth.AuthURL(state), http.StatusFound)
}

func (a *App) handleGitHubCallback(w http.ResponseWriter, r *http.Request) {
	// Validate state
	stateCookie, err := r.Cookie("oauth_state")
	if err != nil || stateCookie.Value == "" || stateCookie.Value != r.URL.Query().Get("state") {
		a.renderError(w, "Invalid OAuth state. Please try logging in again.", http.StatusBadRequest)
		return
	}

	// Clear state cookie
	http.SetCookie(w, &http.Cookie{
		Name:     "oauth_state",
		Value:    "",
		Path:     "/",
		MaxAge:   -1,
		HttpOnly: true,
		Secure:   a.isSecure(),
		SameSite: http.SameSiteLaxMode,
	})

	code := r.URL.Query().Get("code")
	if code == "" {
		a.renderError(w, "No authorization code received from GitHub.", http.StatusBadRequest)
		return
	}

	// Exchange code for token
	accessToken, err := a.OAuth.ExchangeCode(code)
	if err != nil {
		log.Printf("oauth exchange error: %v", err)
		a.renderError(w, "Failed to authenticate with GitHub. Please try again.", http.StatusInternalServerError)
		return
	}

	// Fetch user info
	ghUser, err := a.OAuth.FetchUser(accessToken)
	if err != nil {
		log.Printf("fetch github user error: %v", err)
		a.renderError(w, "Failed to fetch your GitHub profile. Please try again.", http.StatusInternalServerError)
		return
	}

	// Upsert user in DB
	user, err := a.DB.UpsertUser(ghUser.ID, ghUser.Login, ghUser.Name, ghUser.AvatarURL, ghUser.Email)
	if err != nil {
		log.Printf("upsert user error: %v", err)
		a.renderError(w, "Failed to create your account. Please try again.", http.StatusInternalServerError)
		return
	}

	// Create session
	sessionToken, err := a.DB.CreateSession(user.ID)
	if err != nil {
		log.Printf("create session error: %v", err)
		a.renderError(w, "Failed to create session. Please try again.", http.StatusInternalServerError)
		return
	}

	http.SetCookie(w, &http.Cookie{
		Name:     "aes_session",
		Value:    sessionToken,
		Path:     "/",
		HttpOnly: true,
		Secure:   a.isSecure(),
		SameSite: http.SameSiteLaxMode,
		MaxAge:   7 * 24 * 3600, // 7 days
	})

	http.Redirect(w, r, "/dashboard", http.StatusSeeOther)
}

func (a *App) handleDashboard(w http.ResponseWriter, r *http.Request) {
	user := userFromCtx(r)
	tokens, err := a.DB.ListUserTokens(user.ID)
	if err != nil {
		log.Printf("list tokens error: %v", err)
		a.renderError(w, "Failed to load your tokens.", http.StatusInternalServerError)
		return
	}

	a.render(w, "dashboard.html", map[string]interface{}{
		"User":      user,
		"Tokens":    tokens,
		"MaxTokens": a.Config.MaxTokensPerUser,
		"CSRFToken": csrfFromCtx(r),
	})
}

var validTokenName = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_-]{0,62}$`)

func (a *App) handleTokenCreate(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	user := userFromCtx(r)

	// Check token limit
	count, err := a.DB.CountUserTokens(user.ID)
	if err != nil {
		a.renderError(w, "Failed to check token count.", http.StatusInternalServerError)
		return
	}
	if count >= a.Config.MaxTokensPerUser {
		a.renderError(w, fmt.Sprintf("You have reached the maximum of %d tokens. Revoke an existing token first.", a.Config.MaxTokensPerUser), http.StatusBadRequest)
		return
	}

	name := strings.TrimSpace(r.FormValue("name"))
	if name == "" {
		a.renderError(w, "Token name is required.", http.StatusBadRequest)
		return
	}
	if !validTokenName.MatchString(name) {
		a.renderError(w, "Token name must be 1-63 characters, start with a letter or number, and contain only letters, numbers, hyphens, and underscores.", http.StatusBadRequest)
		return
	}

	// Namespace: github_login-user_name
	fullName := user.GitHubLogin + "-" + name

	// Create in tokens.json
	rawToken, err := a.Tokens.CreateToken(fullName)
	if err != nil {
		log.Printf("create token error: %v", err)
		a.renderError(w, "Failed to create token. Please try again.", http.StatusInternalServerError)
		return
	}

	// Record ownership in DB
	if err := a.DB.CreateUserToken(user.ID, fullName); err != nil {
		log.Printf("record token ownership error: %v", err)
		// Token was created in tokens.json but DB record failed — try to revoke
		a.Tokens.RevokeToken(fullName)
		a.renderError(w, "Failed to record token. Please try again.", http.StatusInternalServerError)
		return
	}

	a.render(w, "token_created.html", map[string]interface{}{
		"User":     user,
		"RawToken": rawToken,
		"Name":     fullName,
	})
}

func (a *App) handleTokenRevoke(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	user := userFromCtx(r)
	name := r.FormValue("name")
	if name == "" {
		a.renderError(w, "Token name is required.", http.StatusBadRequest)
		return
	}

	// Verify ownership
	if err := a.DB.DeleteUserToken(user.ID, name); err != nil {
		a.renderError(w, "Token not found or you don't own it.", http.StatusBadRequest)
		return
	}

	// Remove from tokens.json
	if err := a.Tokens.RevokeToken(name); err != nil {
		log.Printf("revoke token from tokens.json error: %v", err)
		// DB record was deleted, but tokens.json removal failed — log and continue
	}

	http.Redirect(w, r, "/dashboard", http.StatusSeeOther)
}

func (a *App) handleLogout(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	cookie, err := r.Cookie("aes_session")
	if err == nil {
		a.DB.DeleteSession(cookie.Value)
	}

	http.SetCookie(w, &http.Cookie{
		Name:   "aes_session",
		Value:  "",
		Path:   "/",
		MaxAge: -1,
	})

	http.Redirect(w, r, "/", http.StatusSeeOther)
}

func (a *App) handleDocs(w http.ResponseWriter, r *http.Request) {
	http.Redirect(w, r, a.Config.DocsURL, http.StatusFound)
}

func (a *App) render(w http.ResponseWriter, name string, data interface{}) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := a.Templates.ExecuteTemplate(w, name, data); err != nil {
		log.Printf("template error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
	}
}

func (a *App) renderError(w http.ResponseWriter, msg string, status int) {
	w.WriteHeader(status)
	a.render(w, "error.html", map[string]interface{}{
		"Error": msg,
	})
}
