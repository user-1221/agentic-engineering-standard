package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// httpClient is used for all outbound GitHub API calls with a timeout.
var httpClient = &http.Client{Timeout: 10 * time.Second}

// GitHubUser is the subset of fields we need from the GitHub API.
type GitHubUser struct {
	ID        int64  `json:"id"`
	Login     string `json:"login"`
	Name      string `json:"name"`
	AvatarURL string `json:"avatar_url"`
	Email     string `json:"email"`
}

// GitHubOAuth handles the GitHub OAuth flow.
type GitHubOAuth struct {
	ClientID     string
	ClientSecret string
	RedirectURI  string
}

// AuthURL returns the GitHub authorization URL with a state parameter.
func (g *GitHubOAuth) AuthURL(state string) string {
	v := url.Values{
		"client_id":    {g.ClientID},
		"redirect_uri": {g.RedirectURI},
		"scope":        {"read:user user:email"},
		"state":        {state},
	}
	return "https://github.com/login/oauth/authorize?" + v.Encode()
}

// ExchangeCode exchanges an authorization code for an access token.
func (g *GitHubOAuth) ExchangeCode(code string) (string, error) {
	v := url.Values{
		"client_id":     {g.ClientID},
		"client_secret": {g.ClientSecret},
		"code":          {code},
	}
	req, err := http.NewRequest("POST", "https://github.com/login/oauth/access_token", strings.NewReader(v.Encode()))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Accept", "application/json")

	resp, err := httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("exchange code: %w", err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	var result struct {
		AccessToken string `json:"access_token"`
		Error       string `json:"error"`
		ErrorDesc   string `json:"error_description"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("parse token response: %w", err)
	}
	if result.Error != "" {
		return "", fmt.Errorf("github oauth: %s — %s", result.Error, result.ErrorDesc)
	}
	return result.AccessToken, nil
}

// FetchUser fetches the authenticated user's profile from GitHub.
func (g *GitHubOAuth) FetchUser(accessToken string) (*GitHubUser, error) {
	req, err := http.NewRequest("GET", "https://api.github.com/user", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+accessToken)
	req.Header.Set("Accept", "application/vnd.github+json")

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetch user: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("github api: %d — %s", resp.StatusCode, body)
	}

	var user GitHubUser
	if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
		return nil, err
	}
	if user.Name == "" {
		user.Name = user.Login
	}
	return &user, nil
}
