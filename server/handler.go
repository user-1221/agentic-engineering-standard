package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
)

// Version is set at build time via ldflags.
var Version = "dev"

// Server holds all dependencies for HTTP handlers.
type Server struct {
	storage  *Storage
	tokens   *TokenStore
	logger   *Logger
	bruteforce *BruteForceLimiter
	config   Config
}

// NewServer creates a new Server with all dependencies.
func NewServer(storage *Storage, tokens *TokenStore, logger *Logger, bf *BruteForceLimiter, cfg Config) *Server {
	return &Server{
		storage:    storage,
		tokens:     tokens,
		logger:     logger,
		bruteforce: bf,
		config:     cfg,
	}
}

// Router returns the HTTP handler with all routes wired up.
func (s *Server) Router() http.Handler {
	mux := http.NewServeMux()

	// Rate limiters per endpoint group
	readIndexRL := NewRateLimiter(60, 60_000_000_000)  // 60 req/min
	readPkgRL := NewRateLimiter(30, 60_000_000_000)    // 30 req/min
	writeRL := NewRateLimiter(10, 60_000_000_000)      // 10 req/min

	// Health check — no rate limit
	mux.HandleFunc("GET /health", s.handleHealth)

	// GET /index.json — public, rate limited
	mux.Handle("GET /index.json", rateLimitMiddleware(readIndexRL, http.HandlerFunc(s.handleGetIndex)))

	// PUT /index.json — authenticated, rate limited
	mux.Handle("PUT /index.json", rateLimitMiddleware(writeRL, http.HandlerFunc(s.handlePutIndex)))

	// GET /packages/{name}/{version}.tar.gz — public, rate limited
	mux.Handle("GET /packages/", rateLimitMiddleware(readPkgRL, http.HandlerFunc(s.handleGetPackage)))

	// PUT /packages/{name}/{version}.tar.gz — authenticated, rate limited
	mux.Handle("PUT /packages/", rateLimitMiddleware(writeRL, http.HandlerFunc(s.handlePutPackage)))

	// Wrap everything with CORS and logging
	var handler http.Handler = mux
	handler = corsMiddleware(handler)
	handler = loggingMiddleware(s.logger, handler)

	return handler
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":  "ok",
		"version": Version,
	})
}

func (s *Server) handleGetIndex(w http.ResponseWriter, r *http.Request) {
	index, err := s.storage.ReadIndex()
	if err != nil {
		s.jsonError(w, "failed to read index", http.StatusInternalServerError)
		s.logger.Log("error", map[string]interface{}{"handler": "GetIndex", "error": err.Error()})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "public, max-age=60")
	json.NewEncoder(w).Encode(index)
}

func (s *Server) handlePutIndex(w http.ResponseWriter, r *http.Request) {
	// Auth required
	token, ok := s.authenticate(w, r)
	if !ok {
		return
	}

	// Read body with size limit
	body := http.MaxBytesReader(w, r.Body, s.config.MaxIndexBytes)
	data, err := io.ReadAll(body)
	if err != nil {
		s.jsonError(w, fmt.Sprintf("request body too large (max %d MB)", s.config.MaxIndexBytes/(1024*1024)), http.StatusRequestEntityTooLarge)
		return
	}

	// Validate index JSON structure
	if _, err := ValidateIndexJSON(data); err != nil {
		s.jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Pretty-print for readability
	var pretty map[string]interface{}
	json.Unmarshal(data, &pretty)
	formatted, _ := json.MarshalIndent(pretty, "", "  ")

	if err := s.storage.WriteIndex(append(formatted, '\n')); err != nil {
		s.jsonError(w, "failed to write index", http.StatusInternalServerError)
		s.logger.Log("error", map[string]interface{}{"handler": "PutIndex", "error": err.Error()})
		return
	}

	s.logger.Audit(map[string]interface{}{
		"action":     "put_index",
		"token_name": token.Name,
		"ip":         clientIP(r),
		"bytes":      len(data),
	})

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "updated"})
}

func (s *Server) handleGetPackage(w http.ResponseWriter, r *http.Request) {
	name, version, err := parsePackagePath(r.URL.Path)
	if err != nil {
		s.jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}

	if err := ValidateName(name); err != nil {
		s.jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}
	if err := ValidateVersion(version); err != nil {
		s.jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}

	f, size, err := s.storage.ReadPackage(name, version)
	if err != nil {
		if strings.Contains(err.Error(), "no such file") {
			s.jsonError(w, fmt.Sprintf("package %s@%s not found", name, version), http.StatusNotFound)
		} else {
			s.jsonError(w, "failed to read package", http.StatusInternalServerError)
			s.logger.Log("error", map[string]interface{}{"handler": "GetPackage", "error": err.Error()})
		}
		return
	}
	defer f.Close()

	w.Header().Set("Content-Type", "application/gzip")
	w.Header().Set("Content-Length", fmt.Sprintf("%d", size))
	w.Header().Set("Cache-Control", "public, max-age=86400, immutable")
	io.Copy(w, f)
}

func (s *Server) handlePutPackage(w http.ResponseWriter, r *http.Request) {
	// Auth required
	token, ok := s.authenticate(w, r)
	if !ok {
		return
	}

	name, version, err := parsePackagePath(r.URL.Path)
	if err != nil {
		s.jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}

	if err := ValidateName(name); err != nil {
		s.jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}
	if err := ValidateVersion(version); err != nil {
		s.jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Check package-level access
	if !s.tokens.CheckPackageAccess(token, name) {
		s.jsonError(w, fmt.Sprintf("token %q is not authorized to publish package %q", token.Name, name), http.StatusForbidden)
		return
	}

	// Immutability check
	if s.storage.PackageExists(name, version) {
		s.jsonError(w, fmt.Sprintf("version %s of '%s' already exists — publish a new version instead", version, name), http.StatusConflict)
		return
	}

	// Read body with size limit
	body := http.MaxBytesReader(w, r.Body, s.config.MaxPackageBytes)
	data, err := io.ReadAll(body)
	if err != nil {
		s.jsonError(w, fmt.Sprintf("request body too large (max %d MB)", s.config.MaxPackageBytes/(1024*1024)), http.StatusRequestEntityTooLarge)
		return
	}

	if len(data) == 0 {
		s.jsonError(w, "empty request body", http.StatusBadRequest)
		return
	}

	if err := s.storage.WritePackage(name, version, data); err != nil {
		if strings.Contains(err.Error(), "already exists") {
			s.jsonError(w, err.Error(), http.StatusConflict)
		} else {
			s.jsonError(w, "failed to store package", http.StatusInternalServerError)
			s.logger.Log("error", map[string]interface{}{"handler": "PutPackage", "error": err.Error()})
		}
		return
	}

	s.logger.Audit(map[string]interface{}{
		"action":     "put_package",
		"package":    name,
		"version":    version,
		"token_name": token.Name,
		"ip":         clientIP(r),
		"bytes":      len(data),
	})

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]string{
		"status":  "created",
		"package": name,
		"version": version,
	})
}

// authenticate checks the Bearer token and handles brute force protection.
// Returns the token entry and true if valid, or writes an error response and returns false.
func (s *Server) authenticate(w http.ResponseWriter, r *http.Request) (*TokenEntry, bool) {
	ip := clientIP(r)

	// Check brute force lockout
	if s.bruteforce.IsBlocked(ip) {
		w.Header().Set("Retry-After", "900")
		s.jsonError(w, "too many authentication failures — try again later", http.StatusTooManyRequests)
		s.logger.Log("warn", map[string]interface{}{
			"event": "auth_blocked",
			"ip":    ip,
		})
		return nil, false
	}

	auth := r.Header.Get("Authorization")
	if auth == "" {
		s.jsonError(w, "Authorization header required", http.StatusUnauthorized)
		return nil, false
	}

	rawToken := strings.TrimPrefix(auth, "Bearer ")
	if rawToken == auth {
		s.jsonError(w, "Authorization must use Bearer scheme", http.StatusUnauthorized)
		return nil, false
	}

	entry, ok := s.tokens.Validate(rawToken)
	if !ok {
		blocked := s.bruteforce.RecordFailure(ip)
		s.logger.Log("warn", map[string]interface{}{
			"event":   "auth_failure",
			"ip":      ip,
			"blocked": blocked,
		})
		if blocked {
			w.Header().Set("Retry-After", "900")
			s.jsonError(w, "too many authentication failures — try again later", http.StatusTooManyRequests)
		} else {
			s.jsonError(w, "invalid token", http.StatusUnauthorized)
		}
		return nil, false
	}

	return entry, true
}

// parsePackagePath extracts name and version from /packages/{name}/{version}.tar.gz
func parsePackagePath(path string) (string, string, error) {
	// Expected: /packages/{name}/{version}.tar.gz
	path = strings.TrimPrefix(path, "/packages/")
	parts := strings.Split(path, "/")
	if len(parts) != 2 {
		return "", "", fmt.Errorf("invalid package path: expected /packages/{name}/{version}.tar.gz")
	}

	name := parts[0]
	filename := parts[1]
	if !strings.HasSuffix(filename, ".tar.gz") {
		return "", "", fmt.Errorf("invalid package path: must end with .tar.gz")
	}
	version := strings.TrimSuffix(filename, ".tar.gz")

	return name, version, nil
}

func (s *Server) jsonError(w http.ResponseWriter, msg string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{"error": msg})
}
