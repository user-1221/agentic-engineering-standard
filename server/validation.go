package main

import (
	"encoding/json"
	"fmt"
	"regexp"
)

var (
	// Matches skill ID pattern from schemas/skill.schema.json: ^[a-z][a-z0-9_-]*$
	// Bounded to 64 chars to prevent abuse.
	namePattern = regexp.MustCompile(`^[a-z][a-z0-9_-]{0,63}$`)

	// Semver with bounded segment lengths to prevent overflow.
	versionPattern = regexp.MustCompile(`^\d{1,5}\.\d{1,5}\.\d{1,5}$`)

	// SHA256 hex digest.
	sha256Pattern = regexp.MustCompile(`^[a-f0-9]{64}$`)

	// Validates that URL fields in the index point to expected package paths.
	urlPattern = regexp.MustCompile(`^packages/[a-z][a-z0-9_-]{0,63}/\d{1,5}\.\d{1,5}\.\d{1,5}\.tar\.gz$`)
)

// ValidateName checks that a package name is safe and valid.
func ValidateName(name string) error {
	if !namePattern.MatchString(name) {
		return fmt.Errorf(
			"invalid package name %q: must be 1-64 lowercase chars starting with a letter (a-z, 0-9, _, -)",
			name,
		)
	}
	return nil
}

// ValidateVersion checks that a version string is valid semver.
func ValidateVersion(version string) error {
	if !versionPattern.MatchString(version) {
		return fmt.Errorf(
			"invalid version %q: must be semver MAJOR.MINOR.PATCH (e.g. 1.0.0)",
			version,
		)
	}
	return nil
}

// ValidateIndexJSON validates that the body is well-formed index JSON.
// Returns the parsed data if valid.
func ValidateIndexJSON(data []byte) (map[string]interface{}, error) {
	var index map[string]interface{}
	if err := json.Unmarshal(data, &index); err != nil {
		return nil, fmt.Errorf("invalid JSON: %w", err)
	}

	pkgs, ok := index["packages"]
	if !ok {
		return nil, fmt.Errorf("missing required field: packages")
	}

	pkgsMap, ok := pkgs.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("packages must be an object")
	}

	// Validate each package entry
	for name, entry := range pkgsMap {
		if err := ValidateName(name); err != nil {
			return nil, fmt.Errorf("package %q: %w", name, err)
		}

		entryMap, ok := entry.(map[string]interface{})
		if !ok {
			return nil, fmt.Errorf("package %q must be an object", name)
		}

		// Validate type field if present
		if typeVal, ok := entryMap["type"]; ok {
			typeStr, ok := typeVal.(string)
			if !ok {
				return nil, fmt.Errorf("package %q: type must be a string", name)
			}
			if typeStr != "skill" && typeStr != "template" {
				return nil, fmt.Errorf("package %q: type must be \"skill\" or \"template\", got %q", name, typeStr)
			}
		}

		// Validate visibility field if present
		if visVal, ok := entryMap["visibility"]; ok {
			visStr, ok := visVal.(string)
			if !ok {
				return nil, fmt.Errorf("package %q: visibility must be a string", name)
			}
			if visStr != "public" && visStr != "private" {
				return nil, fmt.Errorf("package %q: visibility must be \"public\" or \"private\", got %q", name, visStr)
			}
		}

		versions, ok := entryMap["versions"]
		if !ok {
			continue // versions is optional in the index
		}

		versionsMap, ok := versions.(map[string]interface{})
		if !ok {
			return nil, fmt.Errorf("package %q: versions must be an object", name)
		}

		for ver, vEntry := range versionsMap {
			if err := ValidateVersion(ver); err != nil {
				return nil, fmt.Errorf("package %q: %w", name, err)
			}

			vEntryMap, ok := vEntry.(map[string]interface{})
			if !ok {
				return nil, fmt.Errorf("package %q version %q must be an object", name, ver)
			}

			// url is required and must match expected path pattern
			urlVal, ok := vEntryMap["url"]
			if !ok {
				return nil, fmt.Errorf("package %q version %q: missing required field: url", name, ver)
			}
			urlStr, ok := urlVal.(string)
			if !ok || !urlPattern.MatchString(urlStr) {
				return nil, fmt.Errorf("package %q version %q: url must match packages/{name}/{version}.tar.gz pattern", name, ver)
			}

			// sha256 is required and must be valid hex
			sha, ok := vEntryMap["sha256"]
			if !ok {
				return nil, fmt.Errorf("package %q version %q: missing required field: sha256", name, ver)
			}
			shaStr, ok := sha.(string)
			if !ok || !sha256Pattern.MatchString(shaStr) {
				return nil, fmt.Errorf("package %q version %q: sha256 must be a 64-char hex string", name, ver)
			}
		}
	}

	return index, nil
}
