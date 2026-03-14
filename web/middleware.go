package main

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

type contextKey string

const (
	ctxUser contextKey = "user"
	ctxCSRF contextKey = "csrf"
)

// sessionAuth loads the user from the session cookie and puts it in context.
// If no valid session, user is nil (handler decides whether to reject).
func sessionAuth(db *DB, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		cookie, err := r.Cookie("aes_session")
		if err == nil && cookie.Value != "" {
			user, err := db.GetSession(cookie.Value)
			if err == nil && user != nil {
				ctx := context.WithValue(r.Context(), ctxUser, user)
				r = r.WithContext(ctx)
			}
		}
		next.ServeHTTP(w, r)
	})
}

// requireAuth redirects to / if no user is in context.
func requireAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if userFromCtx(r) == nil {
			http.Redirect(w, r, "/", http.StatusSeeOther)
			return
		}
		next(w, r)
	}
}

// csrfProtect implements double-submit cookie CSRF protection.
func csrfProtect(secure bool, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Read or set CSRF cookie
		var csrfToken string
		cookie, err := r.Cookie("aes_csrf")
		if err != nil || cookie.Value == "" {
			raw := make([]byte, 16)
			rand.Read(raw)
			csrfToken = hex.EncodeToString(raw)
			http.SetCookie(w, &http.Cookie{
				Name:     "aes_csrf",
				Value:    csrfToken,
				Path:     "/",
				HttpOnly: true,
				Secure:   secure,
				SameSite: http.SameSiteLaxMode,
				MaxAge:   86400,
			})
		} else {
			csrfToken = cookie.Value
		}

		ctx := context.WithValue(r.Context(), ctxCSRF, csrfToken)
		r = r.WithContext(ctx)

		// Validate on POST
		if r.Method == "POST" {
			formToken := r.FormValue("csrf_token")
			if formToken == "" || subtle.ConstantTimeCompare([]byte(formToken), []byte(csrfToken)) != 1 {
				http.Error(w, "Invalid CSRF token", http.StatusForbidden)
				return
			}
		}

		next.ServeHTTP(w, r)
	})
}

// webSecurityHeaders adds standard security headers for the web dashboard.
func webSecurityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
		w.Header().Set("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; font-src https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; img-src 'self' https://avatars.githubusercontent.com")
		w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
		next.ServeHTTP(w, r)
	})
}

// requestLogger logs each request.
func requestLogger(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rw := &responseWriter{ResponseWriter: w, status: 200}
		next.ServeHTTP(rw, r)
		log.Printf("%s %s %d %s", r.Method, r.URL.Path, rw.status, time.Since(start).Round(time.Millisecond))
	})
}

type responseWriter struct {
	http.ResponseWriter
	status int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.status = code
	rw.ResponseWriter.WriteHeader(code)
}

func userFromCtx(r *http.Request) *User {
	u, _ := r.Context().Value(ctxUser).(*User)
	return u
}

func csrfFromCtx(r *http.Request) string {
	s, _ := r.Context().Value(ctxCSRF).(string)
	return s
}

// webRateLimiter implements per-IP rate limiting for the web service.
type webRateLimiter struct {
	mu      sync.Mutex
	buckets map[string]*webBucket
	limit   int
	window  time.Duration
}

type webBucket struct {
	count   int
	resetAt time.Time
}

func newWebRateLimiter(limit int, window time.Duration) *webRateLimiter {
	rl := &webRateLimiter{
		buckets: make(map[string]*webBucket),
		limit:   limit,
		window:  window,
	}
	go func() {
		for {
			time.Sleep(5 * time.Minute)
			rl.mu.Lock()
			now := time.Now()
			for ip, b := range rl.buckets {
				if now.After(b.resetAt) {
					delete(rl.buckets, ip)
				}
			}
			rl.mu.Unlock()
		}
	}()
	return rl
}

func (rl *webRateLimiter) allow(ip string) (bool, int) {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	b, ok := rl.buckets[ip]
	if !ok || now.After(b.resetAt) {
		rl.buckets[ip] = &webBucket{count: 1, resetAt: now.Add(rl.window)}
		return true, 0
	}
	b.count++
	if b.count > rl.limit {
		secs := int(time.Until(b.resetAt).Seconds())
		if secs < 1 {
			secs = 1
		}
		return false, secs
	}
	return true, 0
}

// webClientIP extracts the client IP, trusting proxy headers only from loopback.
func webClientIP(r *http.Request) string {
	addr := r.RemoteAddr
	if idx := strings.LastIndex(addr, ":"); idx != -1 {
		addr = addr[:idx]
	}
	if addr == "127.0.0.1" || addr == "::1" {
		if ip := r.Header.Get("X-Real-IP"); ip != "" {
			return ip
		}
		if ip := r.Header.Get("X-Forwarded-For"); ip != "" {
			return strings.TrimSpace(strings.Split(ip, ",")[0])
		}
	}
	return addr
}

// rateLimitHandler wraps a handler with per-IP rate limiting.
func rateLimitHandler(rl *webRateLimiter, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ip := webClientIP(r)
		ok, retryAfter := rl.allow(ip)
		if !ok {
			w.Header().Set("Retry-After", fmt.Sprintf("%d", retryAfter))
			http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
			return
		}
		next(w, r)
	}
}
