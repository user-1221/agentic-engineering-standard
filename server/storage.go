package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Storage handles all filesystem operations with atomic writes and backups.
type Storage struct {
	dataDir   string
	backupDir string
	indexMu   sync.Mutex // serializes index.json writes
}

func NewStorage(dataDir, backupDir string) (*Storage, error) {
	// Ensure directories exist
	for _, dir := range []string{
		dataDir,
		filepath.Join(dataDir, "packages"),
		backupDir,
	} {
		if err := os.MkdirAll(dir, 0750); err != nil {
			return nil, fmt.Errorf("create directory %s: %w", dir, err)
		}
	}

	// Ensure index.json exists
	indexPath := filepath.Join(dataDir, "index.json")
	if _, err := os.Stat(indexPath); os.IsNotExist(err) {
		if err := atomicWrite(indexPath, []byte(`{"packages":{}}`+"\n")); err != nil {
			return nil, fmt.Errorf("create initial index.json: %w", err)
		}
	}

	return &Storage{dataDir: dataDir, backupDir: backupDir}, nil
}

// ReadIndex reads and parses index.json.
func (s *Storage) ReadIndex() (map[string]interface{}, error) {
	data, err := os.ReadFile(filepath.Join(s.dataDir, "index.json"))
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]interface{}{"packages": map[string]interface{}{}}, nil
		}
		return nil, err
	}
	var index map[string]interface{}
	if err := json.Unmarshal(data, &index); err != nil {
		return nil, fmt.Errorf("parse index.json: %w", err)
	}
	return index, nil
}

// WriteIndex atomically writes index.json with backup-on-write.
func (s *Storage) WriteIndex(data []byte) error {
	s.indexMu.Lock()
	defer s.indexMu.Unlock()

	indexPath := filepath.Join(s.dataDir, "index.json")

	// Backup current index before overwriting
	if _, err := os.Stat(indexPath); err == nil {
		ts := time.Now().UTC().Format("2006-01-02T15-04-05Z")
		backupPath := filepath.Join(s.backupDir, "index.json."+ts)
		src, err := os.ReadFile(indexPath)
		if err == nil {
			_ = os.WriteFile(backupPath, src, 0640)
		}
	}

	return atomicWrite(indexPath, data)
}

// ReadPackage opens a package tarball for reading. Caller must close the file.
func (s *Storage) ReadPackage(name, version string) (*os.File, int64, error) {
	path := filepath.Join(s.dataDir, "packages", name, version+".tar.gz")

	// Containment check
	absPath, err := filepath.Abs(path)
	if err != nil {
		return nil, 0, fmt.Errorf("resolve path: %w", err)
	}
	absData, _ := filepath.Abs(filepath.Join(s.dataDir, "packages"))
	if !isSubpath(absPath, absData) {
		return nil, 0, fmt.Errorf("path traversal blocked")
	}

	info, err := os.Lstat(path)
	if err != nil {
		return nil, 0, err
	}
	// Reject symlinks
	if info.Mode()&os.ModeSymlink != 0 {
		return nil, 0, fmt.Errorf("symlink not allowed: %s", path)
	}

	f, err := os.Open(path)
	if err != nil {
		return nil, 0, err
	}
	return f, info.Size(), nil
}

// WritePackage atomically writes a package tarball. Returns error if it already exists (immutability).
func (s *Storage) WritePackage(name, version string, data []byte) error {
	pkgDir := filepath.Join(s.dataDir, "packages", name)
	path := filepath.Join(pkgDir, version+".tar.gz")

	// Containment check
	absPath, err := filepath.Abs(path)
	if err != nil {
		return fmt.Errorf("resolve path: %w", err)
	}
	absData, _ := filepath.Abs(filepath.Join(s.dataDir, "packages"))
	if !isSubpath(absPath, absData) {
		return fmt.Errorf("path traversal blocked")
	}

	// Immutability: reject if already exists
	if _, err := os.Lstat(path); err == nil {
		return fmt.Errorf("version %s of '%s' already exists", version, name)
	}

	if err := os.MkdirAll(pkgDir, 0750); err != nil {
		return fmt.Errorf("create package directory: %w", err)
	}

	return atomicWrite(path, data)
}

// PackageExists checks if a package version already exists.
func (s *Storage) PackageExists(name, version string) bool {
	path := filepath.Join(s.dataDir, "packages", name, version+".tar.gz")
	_, err := os.Stat(path)
	return err == nil
}

// atomicWrite writes data to a temp file then renames it into place.
func atomicWrite(path string, data []byte) error {
	dir := filepath.Dir(path)
	tmp, err := os.CreateTemp(dir, ".tmp-*")
	if err != nil {
		return fmt.Errorf("create temp file: %w", err)
	}
	tmpName := tmp.Name()

	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		os.Remove(tmpName)
		return fmt.Errorf("write temp file: %w", err)
	}
	if err := tmp.Close(); err != nil {
		os.Remove(tmpName)
		return fmt.Errorf("close temp file: %w", err)
	}

	if err := os.Chmod(tmpName, 0640); err != nil {
		os.Remove(tmpName)
		return fmt.Errorf("chmod temp file: %w", err)
	}

	if err := os.Rename(tmpName, path); err != nil {
		os.Remove(tmpName)
		return fmt.Errorf("rename temp file: %w", err)
	}
	return nil
}

// atomicWriteFromReader writes from a reader with a size limit.
func atomicWriteFromReader(path string, r io.Reader, limit int64) ([]byte, error) {
	dir := filepath.Dir(path)
	tmp, err := os.CreateTemp(dir, ".tmp-*")
	if err != nil {
		return nil, fmt.Errorf("create temp file: %w", err)
	}
	tmpName := tmp.Name()

	lr := io.LimitReader(r, limit+1) // +1 to detect overflow
	n, err := io.Copy(tmp, lr)
	if err != nil {
		tmp.Close()
		os.Remove(tmpName)
		return nil, fmt.Errorf("write temp file: %w", err)
	}
	if n > limit {
		tmp.Close()
		os.Remove(tmpName)
		return nil, fmt.Errorf("body exceeds maximum size of %d bytes", limit)
	}
	if err := tmp.Close(); err != nil {
		os.Remove(tmpName)
		return nil, fmt.Errorf("close temp file: %w", err)
	}

	// Read back for returning
	data, err := os.ReadFile(tmpName)
	if err != nil {
		os.Remove(tmpName)
		return nil, err
	}

	if err := os.Chmod(tmpName, 0640); err != nil {
		os.Remove(tmpName)
		return nil, err
	}
	if err := os.Rename(tmpName, path); err != nil {
		os.Remove(tmpName)
		return nil, err
	}
	return data, nil
}

// isSubpath checks that child is under parent.
func isSubpath(child, parent string) bool {
	rel, err := filepath.Rel(parent, child)
	if err != nil {
		return false
	}
	// Must not start with ".."
	return len(rel) > 0 && rel[0] != '.'
}
