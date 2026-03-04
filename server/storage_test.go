package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestStorageInit(t *testing.T) {
	dir := t.TempDir()
	dataDir := filepath.Join(dir, "data")
	backupDir := filepath.Join(dir, "backups")

	s, err := NewStorage(dataDir, backupDir)
	if err != nil {
		t.Fatal(err)
	}

	// Index should exist with empty packages
	index, err := s.ReadIndex()
	if err != nil {
		t.Fatal(err)
	}
	pkgs, ok := index["packages"]
	if !ok {
		t.Error("index should have packages key")
	}
	pkgsMap, ok := pkgs.(map[string]interface{})
	if !ok || len(pkgsMap) != 0 {
		t.Error("packages should be empty initially")
	}
}

func TestWriteAndReadPackage(t *testing.T) {
	dir := t.TempDir()
	s, _ := NewStorage(filepath.Join(dir, "data"), filepath.Join(dir, "backups"))

	content := []byte("fake tarball data")
	if err := s.WritePackage("deploy", "1.0.0", content); err != nil {
		t.Fatal(err)
	}

	f, size, err := s.ReadPackage("deploy", "1.0.0")
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()

	if size != int64(len(content)) {
		t.Errorf("size mismatch: got %d, want %d", size, len(content))
	}

	buf := make([]byte, size)
	f.Read(buf)
	if string(buf) != string(content) {
		t.Error("content mismatch")
	}
}

func TestImmutability(t *testing.T) {
	dir := t.TempDir()
	s, _ := NewStorage(filepath.Join(dir, "data"), filepath.Join(dir, "backups"))

	s.WritePackage("deploy", "1.0.0", []byte("v1"))
	err := s.WritePackage("deploy", "1.0.0", []byte("v1-modified"))
	if err == nil {
		t.Error("duplicate write should fail")
	}
}

func TestPackageExists(t *testing.T) {
	dir := t.TempDir()
	s, _ := NewStorage(filepath.Join(dir, "data"), filepath.Join(dir, "backups"))

	if s.PackageExists("deploy", "1.0.0") {
		t.Error("should not exist before write")
	}

	s.WritePackage("deploy", "1.0.0", []byte("content"))

	if !s.PackageExists("deploy", "1.0.0") {
		t.Error("should exist after write")
	}
}

func TestIndexBackupOnWrite(t *testing.T) {
	dir := t.TempDir()
	dataDir := filepath.Join(dir, "data")
	backupDir := filepath.Join(dir, "backups")
	s, _ := NewStorage(dataDir, backupDir)

	// Write index twice
	s.WriteIndex([]byte(`{"packages":{"v1":{}}}`))
	s.WriteIndex([]byte(`{"packages":{"v2":{}}}`))

	// Should have at least one backup
	entries, _ := os.ReadDir(backupDir)
	if len(entries) < 1 {
		t.Error("should have at least one backup")
	}
}

func TestReadNonexistentPackage(t *testing.T) {
	dir := t.TempDir()
	s, _ := NewStorage(filepath.Join(dir, "data"), filepath.Join(dir, "backups"))

	_, _, err := s.ReadPackage("nonexistent", "1.0.0")
	if err == nil {
		t.Error("reading nonexistent package should fail")
	}
}

func TestPathContainment(t *testing.T) {
	if isSubpath("/data/packages/../../etc/passwd", "/data/packages") {
		t.Error("path traversal should be blocked")
	}
	if !isSubpath("/data/packages/deploy/1.0.0.tar.gz", "/data/packages") {
		t.Error("valid subpath should be allowed")
	}
}
