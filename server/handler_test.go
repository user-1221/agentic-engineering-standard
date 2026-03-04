package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http/httptest"
	"path/filepath"
	"testing"
	"time"
)

func setupTestServer(t *testing.T) (*Server, string) {
	t.Helper()
	dir := t.TempDir()
	storage, _ := NewStorage(filepath.Join(dir, "data"), filepath.Join(dir, "backups"))
	tokens, _ := NewTokenStore(filepath.Join(dir, "tokens.json"), "")
	logger, _ := NewLogger("error", "") // suppress logs in tests
	bf := NewBruteForceLimiter(5, 15*time.Minute)
	cfg := LoadConfig()
	cfg.MaxPackageBytes = 1024 * 1024
	cfg.MaxIndexBytes = 1024 * 1024

	raw, _ := tokens.CreateToken("test")
	srv := NewServer(storage, tokens, logger, bf, cfg)
	return srv, raw
}

func TestHealthEndpoint(t *testing.T) {
	srv, _ := setupTestServer(t)
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 200 {
		t.Errorf("health status: got %d, want 200", w.Code)
	}

	var body map[string]string
	json.Unmarshal(w.Body.Bytes(), &body)
	if body["status"] != "ok" {
		t.Errorf("health body: got %v", body)
	}
}

func TestGetEmptyIndex(t *testing.T) {
	srv, _ := setupTestServer(t)
	req := httptest.NewRequest("GET", "/index.json", nil)
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 200 {
		t.Errorf("index status: got %d, want 200", w.Code)
	}

	var body map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &body)
	if _, ok := body["packages"]; !ok {
		t.Error("index should have packages key")
	}
}

func TestPutPackageRequiresAuth(t *testing.T) {
	srv, _ := setupTestServer(t)
	body := bytes.NewReader([]byte("fake tarball"))
	req := httptest.NewRequest("PUT", "/packages/deploy/1.0.0.tar.gz", body)
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 401 {
		t.Errorf("unauthenticated PUT: got %d, want 401", w.Code)
	}
}

func TestPutAndGetPackage(t *testing.T) {
	srv, token := setupTestServer(t)
	content := []byte("fake tarball content for testing")

	// PUT
	putReq := httptest.NewRequest("PUT", "/packages/deploy/1.0.0.tar.gz", bytes.NewReader(content))
	putReq.Header.Set("Authorization", "Bearer "+token)
	putReq.Header.Set("Content-Type", "application/gzip")
	putW := httptest.NewRecorder()
	srv.Router().ServeHTTP(putW, putReq)

	if putW.Code != 201 {
		t.Errorf("PUT package: got %d, want 201. Body: %s", putW.Code, putW.Body.String())
	}

	// GET
	getReq := httptest.NewRequest("GET", "/packages/deploy/1.0.0.tar.gz", nil)
	getW := httptest.NewRecorder()
	srv.Router().ServeHTTP(getW, getReq)

	if getW.Code != 200 {
		t.Errorf("GET package: got %d, want 200", getW.Code)
	}
	body, _ := io.ReadAll(getW.Body)
	if !bytes.Equal(body, content) {
		t.Error("downloaded content doesn't match uploaded content")
	}
}

func TestDuplicateUploadReturns409(t *testing.T) {
	srv, token := setupTestServer(t)
	content := []byte("tarball")

	// First upload
	req1 := httptest.NewRequest("PUT", "/packages/deploy/1.0.0.tar.gz", bytes.NewReader(content))
	req1.Header.Set("Authorization", "Bearer "+token)
	w1 := httptest.NewRecorder()
	srv.Router().ServeHTTP(w1, req1)

	// Duplicate
	req2 := httptest.NewRequest("PUT", "/packages/deploy/1.0.0.tar.gz", bytes.NewReader(content))
	req2.Header.Set("Authorization", "Bearer "+token)
	w2 := httptest.NewRecorder()
	srv.Router().ServeHTTP(w2, req2)

	if w2.Code != 409 {
		t.Errorf("duplicate PUT: got %d, want 409", w2.Code)
	}
}

func TestInvalidPackageName(t *testing.T) {
	srv, _ := setupTestServer(t)
	req := httptest.NewRequest("GET", "/packages/INVALID/1.0.0.tar.gz", nil)
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 400 {
		t.Errorf("invalid name: got %d, want 400", w.Code)
	}
}

func TestInvalidVersion(t *testing.T) {
	srv, _ := setupTestServer(t)
	req := httptest.NewRequest("GET", "/packages/deploy/bad.tar.gz", nil)
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 400 {
		t.Errorf("invalid version: got %d, want 400", w.Code)
	}
}

func TestPutIndexRequiresAuth(t *testing.T) {
	srv, _ := setupTestServer(t)
	body := bytes.NewReader([]byte(`{"packages":{}}`))
	req := httptest.NewRequest("PUT", "/index.json", body)
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 401 {
		t.Errorf("unauthenticated PUT index: got %d, want 401", w.Code)
	}
}

func TestPutAndGetIndex(t *testing.T) {
	srv, token := setupTestServer(t)

	indexData := `{"packages":{"deploy":{"description":"Deploy","latest":"1.0.0","versions":{"1.0.0":{"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}}}}}`

	// PUT index
	putReq := httptest.NewRequest("PUT", "/index.json", bytes.NewReader([]byte(indexData)))
	putReq.Header.Set("Authorization", "Bearer "+token)
	putReq.Header.Set("Content-Type", "application/json")
	putW := httptest.NewRecorder()
	srv.Router().ServeHTTP(putW, putReq)

	if putW.Code != 200 {
		t.Errorf("PUT index: got %d, want 200. Body: %s", putW.Code, putW.Body.String())
	}

	// GET index
	getReq := httptest.NewRequest("GET", "/index.json", nil)
	getW := httptest.NewRecorder()
	srv.Router().ServeHTTP(getW, getReq)

	var index map[string]interface{}
	json.Unmarshal(getW.Body.Bytes(), &index)
	pkgs := index["packages"].(map[string]interface{})
	if _, ok := pkgs["deploy"]; !ok {
		t.Error("index should contain 'deploy' package after PUT")
	}
}

func TestPutIndexRejectsInvalidJSON(t *testing.T) {
	srv, token := setupTestServer(t)

	req := httptest.NewRequest("PUT", "/index.json", bytes.NewReader([]byte("not json")))
	req.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 400 {
		t.Errorf("invalid JSON index: got %d, want 400", w.Code)
	}
}

func TestWrongTokenReturns401(t *testing.T) {
	srv, _ := setupTestServer(t)
	req := httptest.NewRequest("PUT", "/packages/deploy/1.0.0.tar.gz", bytes.NewReader([]byte("data")))
	req.Header.Set("Authorization", "Bearer wrong_token")
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 401 {
		t.Errorf("wrong token: got %d, want 401", w.Code)
	}
}

func TestNonexistentPackageReturns404(t *testing.T) {
	srv, _ := setupTestServer(t)
	req := httptest.NewRequest("GET", "/packages/nonexistent/1.0.0.tar.gz", nil)
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 404 {
		t.Errorf("nonexistent package: got %d, want 404", w.Code)
	}
}

func TestCORSHeaders(t *testing.T) {
	srv, _ := setupTestServer(t)

	// OPTIONS preflight
	req := httptest.NewRequest("OPTIONS", "/index.json", nil)
	w := httptest.NewRecorder()
	srv.Router().ServeHTTP(w, req)

	if w.Code != 204 {
		t.Errorf("OPTIONS: got %d, want 204", w.Code)
	}
	if w.Header().Get("Access-Control-Allow-Origin") != "*" {
		t.Error("missing CORS Allow-Origin header")
	}
	if w.Header().Get("Access-Control-Allow-Methods") == "" {
		t.Error("missing CORS Allow-Methods header")
	}
}

func TestParsePackagePath(t *testing.T) {
	tests := []struct {
		path    string
		name    string
		version string
		err     bool
	}{
		{"/packages/deploy/1.0.0.tar.gz", "deploy", "1.0.0", false},
		{"/packages/my-skill/2.1.0.tar.gz", "my-skill", "2.1.0", false},
		{"/packages/deploy/", "", "", true},
		{"/packages/", "", "", true},
		{"/packages/deploy/1.0.0.zip", "", "", true},
	}

	for _, tt := range tests {
		name, version, err := parsePackagePath(tt.path)
		if tt.err && err == nil {
			t.Errorf("parsePackagePath(%q): expected error", tt.path)
		}
		if !tt.err && err != nil {
			t.Errorf("parsePackagePath(%q): unexpected error: %v", tt.path, err)
		}
		if name != tt.name || version != tt.version {
			t.Errorf("parsePackagePath(%q): got (%q, %q), want (%q, %q)", tt.path, name, version, tt.name, tt.version)
		}
	}
}
