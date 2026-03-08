package main

import (
	"testing"
)

func TestValidateName(t *testing.T) {
	valid := []string{"deploy", "ml-train", "my_skill", "a", "abc123"}
	for _, name := range valid {
		if err := ValidateName(name); err != nil {
			t.Errorf("ValidateName(%q) should be valid, got: %v", name, err)
		}
	}

	invalid := []string{
		"",
		"UPPERCASE",
		"has spaces",
		"123start",
		"-starts-with-dash",
		"_starts-with-underscore",
		"has.dot",
		"has/slash",
		"has\\backslash",
		"has\x00null",
		"a" + string(make([]byte, 64)), // too long (65 chars)
		"../traversal",
	}
	for _, name := range invalid {
		if err := ValidateName(name); err == nil {
			t.Errorf("ValidateName(%q) should be invalid", name)
		}
	}
}

func TestValidateVersion(t *testing.T) {
	valid := []string{"0.0.0", "1.0.0", "1.2.3", "10.20.30", "99999.99999.99999"}
	for _, v := range valid {
		if err := ValidateVersion(v); err != nil {
			t.Errorf("ValidateVersion(%q) should be valid, got: %v", v, err)
		}
	}

	invalid := []string{
		"",
		"1",
		"1.0",
		"v1.0.0",
		"1.0.0-beta",
		"1.0.0.0",
		"abc",
		"1.0.0/../../etc/passwd",
		"999999.0.0", // 6 digits
	}
	for _, v := range invalid {
		if err := ValidateVersion(v); err == nil {
			t.Errorf("ValidateVersion(%q) should be invalid", v)
		}
	}
}

func TestValidateIndexJSON(t *testing.T) {
	// Valid minimal index
	valid := `{"packages":{}}`
	if _, err := ValidateIndexJSON([]byte(valid)); err != nil {
		t.Errorf("valid index rejected: %v", err)
	}

	// Valid with a package
	validFull := `{
		"packages": {
			"deploy": {
				"description": "Deploy",
				"latest": "1.0.0",
				"versions": {
					"1.0.0": {
						"url": "packages/deploy/1.0.0.tar.gz",
						"sha256": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
					}
				}
			}
		}
	}`
	if _, err := ValidateIndexJSON([]byte(validFull)); err != nil {
		t.Errorf("valid full index rejected: %v", err)
	}

	// Invalid: not JSON
	if _, err := ValidateIndexJSON([]byte("not json")); err == nil {
		t.Error("non-JSON should be rejected")
	}

	// Invalid: missing packages
	if _, err := ValidateIndexJSON([]byte(`{"foo":"bar"}`)); err == nil {
		t.Error("missing packages key should be rejected")
	}

	// Invalid: bad package name
	if _, err := ValidateIndexJSON([]byte(`{"packages":{"INVALID":{}}}`)); err == nil {
		t.Error("uppercase package name should be rejected")
	}

	// Invalid: bad version
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"versions": {
					"bad": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err == nil {
		t.Error("bad version string should be rejected")
	}

	// Invalid: missing sha256
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz"}
				}
			}
		}
	}`)); err == nil {
		t.Error("missing sha256 should be rejected")
	}

	// Invalid: bad sha256 length
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"tooshort"}
				}
			}
		}
	}`)); err == nil {
		t.Error("short sha256 should be rejected")
	}

	// Valid: type = "skill"
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"type": "skill",
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err != nil {
		t.Errorf("type=skill should be valid, got: %v", err)
	}

	// Valid: type = "template"
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"ml-pipeline": {
				"type": "template",
				"versions": {
					"2.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err != nil {
		t.Errorf("type=template should be valid, got: %v", err)
	}

	// Valid: no type field (backward compat)
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err != nil {
		t.Errorf("no type field should be valid (backward compat), got: %v", err)
	}

	// Invalid: type = "invalid"
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"type": "invalid",
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err == nil {
		t.Error("invalid type value should be rejected")
	}

	// Invalid: url with path traversal
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"versions": {
					"1.0.0": {"url":"../../etc/passwd","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err == nil {
		t.Error("path traversal url should be rejected")
	}

	// Invalid: type is a number
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"type": 123,
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err == nil {
		t.Error("non-string type should be rejected")
	}

	// Valid: visibility = "public"
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"visibility": "public",
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err != nil {
		t.Errorf("visibility=public should be valid, got: %v", err)
	}

	// Valid: visibility = "private"
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"visibility": "private",
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err != nil {
		t.Errorf("visibility=private should be valid, got: %v", err)
	}

	// Valid: no visibility field (backward compat)
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err != nil {
		t.Errorf("no visibility field should be valid (backward compat), got: %v", err)
	}

	// Invalid: visibility = "unlisted"
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"visibility": "unlisted",
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err == nil {
		t.Error("visibility=unlisted should be rejected")
	}

	// Invalid: visibility = 123
	if _, err := ValidateIndexJSON([]byte(`{
		"packages": {
			"deploy": {
				"visibility": 123,
				"versions": {
					"1.0.0": {"url":"packages/deploy/1.0.0.tar.gz","sha256":"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}
				}
			}
		}
	}`)); err == nil {
		t.Error("non-string visibility should be rejected")
	}
}
