// Package config shows where chiper keeps its runtime secrets when onboarding
// a new codebase: environment variables are read here and nowhere else.
// Reference: chiper-codebase-onboarding ("secrets": "env vars via config/config.go").
package config

import (
	"fmt"
	"os"
	"strings"
	"time"
)

// Settings mirrors the environment variables the service expects.
type Settings struct {
	DatabaseURL string
	APIKey      string
	LogLevel    string
	Timeout     time.Duration
}

// Load reads configuration from the environment. Missing optional values fall
// back to safe defaults; a missing DatabaseURL is a hard failure because the
// service cannot start without it.
func Load() (Settings, error) {
	s := Settings{
		DatabaseURL: os.Getenv("APP_DATABASE_URL"),
		APIKey:      os.Getenv("APP_API_KEY"),
		LogLevel:    strings.ToLower(orDefault(os.Getenv("APP_LOG_LEVEL"), "info")),
	}
	if s.DatabaseURL == "" {
		return s, fmt.Errorf("APP_DATABASE_URL is required")
	}
	timeout := orDefault(os.Getenv("APP_TIMEOUT"), "10s")
	d, err := time.ParseDuration(timeout)
	if err != nil {
		return s, fmt.Errorf("APP_TIMEOUT %q is not a duration: %w", timeout, err)
	}
	s.Timeout = d
	return s, nil
}

// Redacted renders the settings safely for logs — secrets never reach stdout.
func (s Settings) Redacted() string {
	return fmt.Sprintf("db=%s api_key=%s log=%s timeout=%s",
		redact(s.DatabaseURL), redact(s.APIKey), s.LogLevel, s.Timeout)
}

func orDefault(v, fallback string) string {
	if v == "" {
		return fallback
	}
	return v
}

func redact(v string) string {
	if v == "" {
		return "<unset>"
	}
	if len(v) <= 8 {
		return "***"
	}
	return v[:4] + "…" + v[len(v)-4:]
}
