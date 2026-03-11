package main

import (
	"html/template"
	"net/http"
	"net/http/httptest"
	"net/url"
	"path/filepath"
	"strings"
	"testing"
)

// setupTestApp creates an App with in-memory templates and a temp DB.
func setupTestApp(t *testing.T) *App {
	t.Helper()
	dir := t.TempDir()

	db, err := OpenDB(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })

	oauth := &GitHubOAuth{
		ClientID:     "test-client-id",
		ClientSecret: "test-client-secret",
		RedirectURI:  "http://localhost:8081/auth/github/callback",
	}

	tokens := NewTokenManager(filepath.Join(dir, "tokens.json"), "")

	cfg := Config{
		ListenAddr:         "127.0.0.1:0",
		DBPath:             filepath.Join(dir, "test.db"),
		TokensFile:         filepath.Join(dir, "tokens.json"),
		SessionSecret:      "test-session-secret",
		GitHubClientID:     "test-client-id",
		GitHubClientSecret: "test-client-secret",
		BaseURL:            "http://localhost:8081",
		DocsURL:            "https://example.com/docs",
		MaxTokensPerUser:   10,
	}

	// Minimal templates for testing (avoids filesystem dependency)
	tmpl := template.Must(template.New("index.html").Parse(`<!DOCTYPE html><html><body>{{if .User}}Logged in as {{.User.GitHubLogin}}{{else}}Welcome{{end}}</body></html>`))
	template.Must(tmpl.New("dashboard.html").Parse(`<!DOCTYPE html><html><body>Dashboard for {{.User.GitHubLogin}} tokens={{len .Tokens}} csrf={{.CSRFToken}}</body></html>`))
	template.Must(tmpl.New("error.html").Parse(`<!DOCTYPE html><html><body>Error: {{.Error}}</body></html>`))
	template.Must(tmpl.New("token_created.html").Parse(`<!DOCTYPE html><html><body>Token {{.Name}} created: {{.RawToken}}</body></html>`))

	return &App{
		DB:        db,
		OAuth:     oauth,
		Tokens:    tokens,
		Config:    cfg,
		Templates: tmpl,
	}
}

// authenticatedRequest adds session and CSRF cookies to a request.
func authenticatedRequest(t *testing.T, app *App, method, path string, form url.Values) *http.Request {
	t.Helper()

	user, err := app.DB.UpsertUser(12345, "testuser", "Test User", "", "test@example.com")
	if err != nil {
		t.Fatal(err)
	}
	sessionToken, err := app.DB.CreateSession(user.ID)
	if err != nil {
		t.Fatal(err)
	}

	var req *http.Request
	if form != nil {
		req = httptest.NewRequest(method, path, strings.NewReader(form.Encode()))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	} else {
		req = httptest.NewRequest(method, path, nil)
	}

	req.AddCookie(&http.Cookie{Name: "aes_session", Value: sessionToken})
	req.AddCookie(&http.Cookie{Name: "aes_csrf", Value: "test-csrf"})
	return req
}

func TestHandleIndex(t *testing.T) {
	app := setupTestApp(t)
	req := httptest.NewRequest("GET", "/", nil)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != 200 {
		t.Errorf("index status: got %d, want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Welcome") {
		t.Errorf("index body should contain 'Welcome', got %q", w.Body.String())
	}
}

func TestHandleIndex_404(t *testing.T) {
	app := setupTestApp(t)
	req := httptest.NewRequest("GET", "/nonexistent", nil)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != 404 {
		t.Errorf("nonexistent path: got %d, want 404", w.Code)
	}
}

func TestHandleLogin_RedirectsToGitHub(t *testing.T) {
	app := setupTestApp(t)
	req := httptest.NewRequest("GET", "/login", nil)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusFound {
		t.Errorf("login status: got %d, want %d", w.Code, http.StatusFound)
	}

	loc := w.Header().Get("Location")
	if !strings.HasPrefix(loc, "https://github.com/login/oauth/authorize") {
		t.Errorf("login should redirect to GitHub, got %q", loc)
	}
	if !strings.Contains(loc, "client_id=test-client-id") {
		t.Errorf("login URL should contain client_id, got %q", loc)
	}

	// Should set state cookie
	cookies := w.Result().Cookies()
	var stateCookie *http.Cookie
	for _, c := range cookies {
		if c.Name == "oauth_state" {
			stateCookie = c
		}
	}
	if stateCookie == nil {
		t.Error("login should set oauth_state cookie")
	}
	if stateCookie != nil && !stateCookie.HttpOnly {
		t.Error("oauth_state cookie should be HttpOnly")
	}
}

func TestHandleGitHubCallback_MissingState(t *testing.T) {
	app := setupTestApp(t)
	req := httptest.NewRequest("GET", "/auth/github/callback?code=abc", nil)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("callback without state: got %d, want %d", w.Code, http.StatusBadRequest)
	}
}

func TestHandleGitHubCallback_StateMismatch(t *testing.T) {
	app := setupTestApp(t)
	req := httptest.NewRequest("GET", "/auth/github/callback?code=abc&state=wrong", nil)
	req.AddCookie(&http.Cookie{Name: "oauth_state", Value: "correct"})
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("callback with wrong state: got %d, want %d", w.Code, http.StatusBadRequest)
	}
}

func TestHandleGitHubCallback_MissingCode(t *testing.T) {
	app := setupTestApp(t)
	req := httptest.NewRequest("GET", "/auth/github/callback?state=abc", nil)
	req.AddCookie(&http.Cookie{Name: "oauth_state", Value: "abc"})
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("callback without code: got %d, want %d", w.Code, http.StatusBadRequest)
	}
}

func TestHandleDashboard_Unauthenticated(t *testing.T) {
	app := setupTestApp(t)
	req := httptest.NewRequest("GET", "/dashboard", nil)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusSeeOther {
		t.Errorf("unauthenticated dashboard: got %d, want %d", w.Code, http.StatusSeeOther)
	}
	if loc := w.Header().Get("Location"); loc != "/" {
		t.Errorf("should redirect to /, got %q", loc)
	}
}

func TestHandleDashboard_Authenticated(t *testing.T) {
	app := setupTestApp(t)
	req := authenticatedRequest(t, app, "GET", "/dashboard", nil)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != 200 {
		t.Errorf("authenticated dashboard: got %d, want 200", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "testuser") {
		t.Errorf("dashboard should show username, got %q", body)
	}
}

func TestHandleTokenCreate_Unauthenticated(t *testing.T) {
	app := setupTestApp(t)
	form := url.Values{"name": {"mytoken"}, "csrf_token": {"x"}}
	req := httptest.NewRequest("POST", "/dashboard/tokens/new", strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	// CSRF middleware fires before auth — rejects with 403 since no valid CSRF cookie
	if w.Code != http.StatusForbidden {
		t.Errorf("unauthenticated token create: got %d, want %d", w.Code, http.StatusForbidden)
	}
}

func TestHandleTokenCreate_Success(t *testing.T) {
	app := setupTestApp(t)
	form := url.Values{"name": {"mytoken"}, "csrf_token": {"test-csrf"}}
	req := authenticatedRequest(t, app, "POST", "/dashboard/tokens/new", form)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != 200 {
		t.Errorf("token create: got %d, want 200", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "aes_tok_") {
		t.Errorf("response should contain raw token, got %q", body)
	}
	if !strings.Contains(body, "testuser-mytoken") {
		t.Errorf("response should contain namespaced token name, got %q", body)
	}
}

func TestHandleTokenCreate_InvalidName(t *testing.T) {
	app := setupTestApp(t)
	form := url.Values{"name": {"invalid name with spaces!"}, "csrf_token": {"test-csrf"}}
	req := authenticatedRequest(t, app, "POST", "/dashboard/tokens/new", form)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("invalid name: got %d, want %d", w.Code, http.StatusBadRequest)
	}
}

func TestHandleTokenCreate_EmptyName(t *testing.T) {
	app := setupTestApp(t)
	form := url.Values{"name": {""}, "csrf_token": {"test-csrf"}}
	req := authenticatedRequest(t, app, "POST", "/dashboard/tokens/new", form)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("empty name: got %d, want %d", w.Code, http.StatusBadRequest)
	}
}

func TestHandleTokenCreate_MaxTokensReached(t *testing.T) {
	app := setupTestApp(t)
	app.Config.MaxTokensPerUser = 2

	// Create 2 tokens
	form1 := url.Values{"name": {"tok1"}, "csrf_token": {"test-csrf"}}
	req1 := authenticatedRequest(t, app, "POST", "/dashboard/tokens/new", form1)
	w1 := httptest.NewRecorder()
	app.Router().ServeHTTP(w1, req1)
	if w1.Code != 200 {
		t.Fatalf("first token: got %d, want 200", w1.Code)
	}

	form2 := url.Values{"name": {"tok2"}, "csrf_token": {"test-csrf"}}
	req2 := authenticatedRequest(t, app, "POST", "/dashboard/tokens/new", form2)
	w2 := httptest.NewRecorder()
	app.Router().ServeHTTP(w2, req2)
	if w2.Code != 200 {
		t.Fatalf("second token: got %d, want 200", w2.Code)
	}

	// Third should fail
	form3 := url.Values{"name": {"tok3"}, "csrf_token": {"test-csrf"}}
	req3 := authenticatedRequest(t, app, "POST", "/dashboard/tokens/new", form3)
	w3 := httptest.NewRecorder()
	app.Router().ServeHTTP(w3, req3)
	if w3.Code != http.StatusBadRequest {
		t.Errorf("over limit: got %d, want %d", w3.Code, http.StatusBadRequest)
	}
}

func TestHandleTokenCreate_MethodNotAllowed(t *testing.T) {
	app := setupTestApp(t)
	req := authenticatedRequest(t, app, "GET", "/dashboard/tokens/new", nil)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("GET token create: got %d, want %d", w.Code, http.StatusMethodNotAllowed)
	}
}

func TestHandleTokenRevoke_Success(t *testing.T) {
	app := setupTestApp(t)

	// Create a token first
	form1 := url.Values{"name": {"mytoken"}, "csrf_token": {"test-csrf"}}
	req1 := authenticatedRequest(t, app, "POST", "/dashboard/tokens/new", form1)
	w1 := httptest.NewRecorder()
	app.Router().ServeHTTP(w1, req1)
	if w1.Code != 200 {
		t.Fatalf("create token: got %d, want 200", w1.Code)
	}

	// Revoke it
	form2 := url.Values{"name": {"testuser-mytoken"}, "csrf_token": {"test-csrf"}}
	req2 := authenticatedRequest(t, app, "POST", "/dashboard/tokens/revoke", form2)
	w2 := httptest.NewRecorder()
	app.Router().ServeHTTP(w2, req2)

	if w2.Code != http.StatusSeeOther {
		t.Errorf("revoke: got %d, want %d", w2.Code, http.StatusSeeOther)
	}
	if loc := w2.Header().Get("Location"); loc != "/dashboard" {
		t.Errorf("revoke redirect: got %q, want /dashboard", loc)
	}
}

func TestHandleTokenRevoke_NotOwned(t *testing.T) {
	app := setupTestApp(t)

	form := url.Values{"name": {"nonexistent-token"}, "csrf_token": {"test-csrf"}}
	req := authenticatedRequest(t, app, "POST", "/dashboard/tokens/revoke", form)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("revoke non-owned: got %d, want %d", w.Code, http.StatusBadRequest)
	}
}

func TestHandleTokenRevoke_EmptyName(t *testing.T) {
	app := setupTestApp(t)

	form := url.Values{"name": {""}, "csrf_token": {"test-csrf"}}
	req := authenticatedRequest(t, app, "POST", "/dashboard/tokens/revoke", form)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("revoke empty name: got %d, want %d", w.Code, http.StatusBadRequest)
	}
}

func TestHandleLogout(t *testing.T) {
	app := setupTestApp(t)

	form := url.Values{"csrf_token": {"test-csrf"}}
	req := authenticatedRequest(t, app, "POST", "/logout", form)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusSeeOther {
		t.Errorf("logout: got %d, want %d", w.Code, http.StatusSeeOther)
	}
	if loc := w.Header().Get("Location"); loc != "/" {
		t.Errorf("logout redirect: got %q, want /", loc)
	}

	// Session cookie should be cleared
	cookies := w.Result().Cookies()
	for _, c := range cookies {
		if c.Name == "aes_session" && c.MaxAge != -1 {
			t.Error("session cookie should have MaxAge=-1 after logout")
		}
	}
}

func TestHandleLogout_MethodNotAllowed(t *testing.T) {
	app := setupTestApp(t)
	req := authenticatedRequest(t, app, "GET", "/logout", nil)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("GET logout: got %d, want %d", w.Code, http.StatusMethodNotAllowed)
	}
}

func TestHandleDocs_Redirect(t *testing.T) {
	app := setupTestApp(t)
	req := httptest.NewRequest("GET", "/docs", nil)
	w := httptest.NewRecorder()
	app.Router().ServeHTTP(w, req)

	if w.Code != http.StatusFound {
		t.Errorf("docs: got %d, want %d", w.Code, http.StatusFound)
	}
	if loc := w.Header().Get("Location"); loc != "https://example.com/docs" {
		t.Errorf("docs redirect: got %q, want %q", loc, "https://example.com/docs")
	}
}

func TestIsSecure(t *testing.T) {
	app := setupTestApp(t)

	app.Config.BaseURL = "https://example.com"
	if !app.isSecure() {
		t.Error("https URL should be secure")
	}

	app.Config.BaseURL = "http://localhost:8081"
	if app.isSecure() {
		t.Error("http URL should not be secure")
	}
}

func TestValidTokenNameRegex(t *testing.T) {
	valid := []string{"mytoken", "my-token", "my_token", "abc123", "a", "A1-b2_C3"}
	for _, name := range valid {
		if !validTokenName.MatchString(name) {
			t.Errorf("expected %q to be valid", name)
		}
	}

	invalid := []string{"", "-starts-with-dash", "_starts-with-underscore", "has spaces", "too-long-" + strings.Repeat("x", 64)}
	for _, name := range invalid {
		if validTokenName.MatchString(name) {
			t.Errorf("expected %q to be invalid", name)
		}
	}
}
