package model

import "time"

// User represents the user account entity.
type User struct {
	ID             int64     `json:"id"`
	Username       string    `json:"username"`
	HashedPassword string    `json:"-"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

// UserResponse is the safe user representation returned in API responses.
type UserResponse struct {
	ID        int64     `json:"id"`
	Username  string    `json:"username"`
	CreatedAt time.Time `json:"created_at"`
}

// RegisterRequest is the payload for user registration.
type RegisterRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// LoginRequest is the payload for user authentication.
type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// AuthResponse is the response returned on successful registration or login.
type AuthResponse struct {
	Token string       `json:"token"`
	User  UserResponse `json:"user"`
}
