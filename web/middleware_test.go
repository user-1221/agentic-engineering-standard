package main

import (
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func TestSessionAuth_NoCookie(t *testing.T) {
	db := setupTestDB(t)

	var gotUser *User
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotUser = userFromCtx(r)
		w.WriteHeader(200)
	})

	handler := sessionAuth(db, inner)
	req := httptest.NewRequest("GET", "/", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if gotUser != nil {
		t.Error("expected nil user when no session cookie")
	}
}

func TestSessionAuth_ValidSession(t *testing.T) {
	db := setupTestDB(t)
	user, _ := db.UpsertUser(12345, "testuser", "Test", "", "")
	token, _ := db.CreateSession(user.ID)

	var gotUser *User
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotUser = userFromCtx(r)
		w.WriteHeader(200)
	})

	handler := sessionAuth(db, inner)
	req := httptest.NewRequest("GET", "/", nil)
	req.AddCookie(&http.Cookie{Name: "aes_session", Value: token})
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if gotUser == nil {
		t.Fatal("expected non-nil user with valid session")
	}
	if gotUser.GitHubLogin != "testuser" {
		t.Errorf("user login: got %q, want %q", gotUser.GitHubLogin, "testuser")
	}
}

func TestSessionAuth_InvalidSession(t *testing.T) {
	db := setupTestDB(t)

	var gotUser *User
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotUser = userFromCtx(r)
		w.WriteHeader(200)
	})

	handler := sessionAuth(db, inner)
	req := httptest.NewRequest("GET", "/", nil)
	req.AddCookie(&http.Cookie{Name: "aes_session", Value: "invalid-token"})
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if gotUser != nil {
		t.Error("expected nil user with invalid session token")
	}
}

func TestRequireAuth_NoUser(t *testing.T) {
	inner := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
	}

	handler := requireAuth(inner)
	req := httptest.NewRequest("GET", "/dashboard", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusSeeOther {
		t.Errorf("status: got %d, want %d", w.Code, http.StatusSeeOther)
	}
	if loc := w.Header().Get("Location"); loc != "/" {
		t.Errorf("redirect location: got %q, want %q", loc, "/")
	}
}

func TestCSRFProtect_SetsCookieOnGET(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// CSRF token should be available in context
		csrf := csrfFromCtx(r)
		if csrf == "" {
			t.Error("expected non-empty CSRF token in context")
		}
		w.WriteHeader(200)
	})

	handler := csrfProtect(false, inner)
	req := httptest.NewRequest("GET", "/", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != 200 {
		t.Errorf("status: got %d, want 200", w.Code)
	}

	// Check that CSRF cookie was set
	cookies := w.Result().Cookies()
	var found bool
	for _, c := range cookies {
		if c.Name == "aes_csrf" && c.Value != "" {
			found = true
		}
	}
	if !found {
		t.Error("expected aes_csrf cookie to be set")
	}
}

func TestCSRFProtect_ReusesCookie(t *testing.T) {
	var gotCSRF string
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotCSRF = csrfFromCtx(r)
		w.WriteHeader(200)
	})

	handler := csrfProtect(false, inner)
	req := httptest.NewRequest("GET", "/", nil)
	req.AddCookie(&http.Cookie{Name: "aes_csrf", Value: "existing-token"})
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if gotCSRF != "existing-token" {
		t.Errorf("csrf from context: got %q, want %q", gotCSRF, "existing-token")
	}
}

func TestCSRFProtect_ValidPOST(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
	})

	handler := csrfProtect(false, inner)
	body := strings.NewReader("csrf_token=test-csrf-value")
	req := httptest.NewRequest("POST", "/action", body)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.AddCookie(&http.Cookie{Name: "aes_csrf", Value: "test-csrf-value"})
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != 200 {
		t.Errorf("valid CSRF POST: got %d, want 200", w.Code)
	}
}

func TestCSRFProtect_InvalidPOST(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
	})

	handler := csrfProtect(false, inner)
	body := strings.NewReader("csrf_token=wrong-value")
	req := httptest.NewRequest("POST", "/action", body)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.AddCookie(&http.Cookie{Name: "aes_csrf", Value: "correct-value"})
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusForbidden {
		t.Errorf("invalid CSRF POST: got %d, want %d", w.Code, http.StatusForbidden)
	}
}

func TestCSRFProtect_MissingFormToken(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
	})

	handler := csrfProtect(false, inner)
	body := strings.NewReader("")
	req := httptest.NewRequest("POST", "/action", body)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.AddCookie(&http.Cookie{Name: "aes_csrf", Value: "some-value"})
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusForbidden {
		t.Errorf("missing form token POST: got %d, want %d", w.Code, http.StatusForbidden)
	}
}

func TestWebSecurityHeaders(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
	})

	handler := webSecurityHeaders(inner)
	req := httptest.NewRequest("GET", "/", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	expected := map[string]string{
		"X-Content-Type-Options":    "nosniff",
		"X-Frame-Options":          "DENY",
		"Strict-Transport-Security": "max-age=63072000; includeSubDomains",
		"Referrer-Policy":           "strict-origin-when-cross-origin",
	}
	for header, want := range expected {
		got := w.Header().Get(header)
		if got != want {
			t.Errorf("%s: got %q, want %q", header, got, want)
		}
	}
	csp := w.Header().Get("Content-Security-Policy")
	if csp == "" {
		t.Error("expected Content-Security-Policy header")
	}
}

func TestRateLimiter_AllowsWithinLimit(t *testing.T) {
	rl := newWebRateLimiter(3, 10*60_000_000_000) // 3 req per 10min (as nanoseconds)

	for i := 0; i < 3; i++ {
		ok, _ := rl.allow("1.2.3.4")
		if !ok {
			t.Errorf("request %d should be allowed", i+1)
		}
	}
}

func TestRateLimiter_BlocksOverLimit(t *testing.T) {
	rl := newWebRateLimiter(2, 10*60_000_000_000)

	rl.allow("1.2.3.4")
	rl.allow("1.2.3.4")
	ok, retryAfter := rl.allow("1.2.3.4")
	if ok {
		t.Error("third request should be blocked")
	}
	if retryAfter <= 0 {
		t.Errorf("retryAfter: got %d, want > 0", retryAfter)
	}
}

func TestRateLimiter_SeparateIPs(t *testing.T) {
	rl := newWebRateLimiter(1, 10*60_000_000_000)

	ok1, _ := rl.allow("1.1.1.1")
	ok2, _ := rl.allow("2.2.2.2")
	if !ok1 || !ok2 {
		t.Error("different IPs should have independent limits")
	}
}

func TestWebClientIP_DirectConnection(t *testing.T) {
	req := httptest.NewRequest("GET", "/", nil)
	req.RemoteAddr = "5.6.7.8:12345"
	if ip := webClientIP(req); ip != "5.6.7.8" {
		t.Errorf("client ip: got %q, want %q", ip, "5.6.7.8")
	}
}

func TestWebClientIP_BehindProxy(t *testing.T) {
	req := httptest.NewRequest("GET", "/", nil)
	req.RemoteAddr = "127.0.0.1:12345"
	req.Header.Set("X-Real-IP", "10.20.30.40")
	if ip := webClientIP(req); ip != "10.20.30.40" {
		t.Errorf("client ip behind proxy: got %q, want %q", ip, "10.20.30.40")
	}
}

func TestWebClientIP_IgnoresProxyHeadersFromExternal(t *testing.T) {
	req := httptest.NewRequest("GET", "/", nil)
	req.RemoteAddr = "5.6.7.8:12345"
	req.Header.Set("X-Real-IP", "spoofed")
	if ip := webClientIP(req); ip != "5.6.7.8" {
		t.Errorf("should ignore X-Real-IP from non-loopback: got %q, want %q", ip, "5.6.7.8")
	}
}

func TestRateLimitHandler(t *testing.T) {
	rl := newWebRateLimiter(1, 10*60_000_000_000)
	inner := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
	}
	handler := rateLimitHandler(rl, inner)

	// First request: OK
	req := httptest.NewRequest("GET", "/", nil)
	req.RemoteAddr = "1.2.3.4:1234"
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != 200 {
		t.Errorf("first request: got %d, want 200", w.Code)
	}

	// Second request: rate limited
	req = httptest.NewRequest("GET", "/", nil)
	req.RemoteAddr = "1.2.3.4:1234"
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusTooManyRequests {
		t.Errorf("second request: got %d, want %d", w.Code, http.StatusTooManyRequests)
	}
	if ra := w.Header().Get("Retry-After"); ra == "" {
		t.Error("expected Retry-After header on rate-limited response")
	}
}

func TestRequestLogger(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(201)
	})

	handler := requestLogger(inner)
	req := httptest.NewRequest("GET", "/test", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != 201 {
		t.Errorf("status: got %d, want 201", w.Code)
	}
}

func TestResponseWriter_CapturesStatus(t *testing.T) {
	rec := httptest.NewRecorder()
	rw := &responseWriter{ResponseWriter: rec, status: 200}
	rw.WriteHeader(404)
	if rw.status != 404 {
		t.Errorf("status: got %d, want 404", rw.status)
	}
}

func TestTokenManager_CreateAndRevoke(t *testing.T) {
	dir := t.TempDir()
	tm := NewTokenManager(filepath.Join(dir, "tokens.json"), "")

	// Create
	raw, err := tm.CreateToken("test-token")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(raw, "aes_tok_") {
		t.Errorf("token should start with aes_tok_, got %q", raw)
	}

	// Create duplicate
	_, err = tm.CreateToken("test-token")
	if err == nil {
		t.Error("expected error for duplicate token name")
	}

	// Revoke
	if err := tm.RevokeToken("test-token"); err != nil {
		t.Fatal(err)
	}

	// Revoke again — should error
	if err := tm.RevokeToken("test-token"); err == nil {
		t.Error("expected error revoking non-existent token")
	}
}

func TestTokenManager_RevokeNonExistent(t *testing.T) {
	dir := t.TempDir()
	tm := NewTokenManager(filepath.Join(dir, "tokens.json"), "")

	// Create a token first so the file exists
	tm.CreateToken("some-token")

	err := tm.RevokeToken("nonexistent")
	if err == nil {
		t.Error("expected error revoking non-existent token")
	}
}
