package handler

import (
	"context"
	"errors"
	"net/http"
	"regexp"
	"strings"
	"time"
	"unicode"

	"github.com/cloudwego/hertz/pkg/app"
	"github.com/maoxiongkai/screenscout-backend/middleware"
	"github.com/maoxiongkai/screenscout-backend/model"
	"github.com/maoxiongkai/screenscout-backend/repo"
	"golang.org/x/crypto/bcrypt"
)

var (
	usernameRegex = regexp.MustCompile(`^[a-zA-Z0-9_.-]{3,55}$`)
	sgtLocation   = time.FixedZone("SGT", 8*3600)
)

// validatePassword ensures password has >= 8 chars, 1 uppercase, 1 lowercase, 1 special character.
func validatePassword(password string) error {
	if len(password) < 8 {
		return errors.New("password must be at least 8 characters long")
	}

	var hasUpper, hasLower, hasSpecial bool
	for _, ch := range password {
		switch {
		case unicode.IsUpper(ch):
			hasUpper = true
		case unicode.IsLower(ch):
			hasLower = true
		case unicode.IsPunct(ch) || unicode.IsSymbol(ch):
			hasSpecial = true
		}
	}

	if !hasUpper {
		return errors.New("password must contain at least 1 uppercase letter")
	}
	if !hasLower {
		return errors.New("password must contain at least 1 lowercase letter")
	}
	if !hasSpecial {
		return errors.New("password must contain at least 1 special character (e.g. !@#$%^&*)")
	}
	return nil
}

// AuthHandler handles authentication HTTP requests.
type AuthHandler struct {
	Repo *repo.UserRepo
}

// NewAuthHandler creates a new AuthHandler.
func NewAuthHandler(r *repo.UserRepo) *AuthHandler {
	return &AuthHandler{Repo: r}
}

// Register handles POST /api/auth/register
func (h *AuthHandler) Register(ctx context.Context, c *app.RequestContext) {
	var req model.RegisterRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{
			"error": "invalid request body",
		})
		return
	}

	username := strings.TrimSpace(req.Username)
	if !usernameRegex.MatchString(username) {
		c.JSON(http.StatusBadRequest, map[string]string{
			"error": "username must be 3-55 characters and contain only letters, numbers, underscores, dashes, or dots",
		})
		return
	}

	if err := validatePassword(req.Password); err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{
			"error": err.Error(),
		})
		return
	}

	// Hash password with bcrypt
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to hash password",
		})
		return
	}

	// Insert into DB
	user, err := h.Repo.CreateUser(ctx, username, string(hashedPassword))
	if err != nil {
		if errors.Is(err, repo.ErrUsernameDuplicate) {
			c.JSON(http.StatusConflict, map[string]string{
				"error": "username is already registered",
			})
			return
		}
		c.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to create user",
		})
		return
	}

	// Generate JWT token
	token, err := middleware.GenerateToken(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to generate authentication token",
		})
		return
	}

	c.JSON(http.StatusCreated, model.AuthResponse{
		Token: token,
		User: model.UserResponse{
			ID:        user.ID,
			Username:  user.Username,
			CreatedAt: user.CreatedAt.In(sgtLocation),
		},
	})
}

// Login handles POST /api/auth/login
func (h *AuthHandler) Login(ctx context.Context, c *app.RequestContext) {
	var req model.LoginRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, map[string]string{
			"error": "invalid request body",
		})
		return
	}

	username := strings.TrimSpace(req.Username)
	if username == "" || req.Password == "" {
		c.JSON(http.StatusBadRequest, map[string]string{
			"error": "username and password are required",
		})
		return
	}

	user, err := h.Repo.GetUserByUsername(ctx, username)
	if err != nil {
		if errors.Is(err, repo.ErrUserNotFound) {
			c.JSON(http.StatusUnauthorized, map[string]string{
				"error": "invalid username or password",
			})
			return
		}
		c.JSON(http.StatusInternalServerError, map[string]string{
			"error": "database error",
		})
		return
	}

	// Compare bcrypt hash
	if err := bcrypt.CompareHashAndPassword([]byte(user.HashedPassword), []byte(req.Password)); err != nil {
		c.JSON(http.StatusUnauthorized, map[string]string{
			"error": "invalid username or password",
		})
		return
	}

	// Generate JWT token
	token, err := middleware.GenerateToken(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to generate authentication token",
		})
		return
	}

	c.JSON(http.StatusOK, model.AuthResponse{
		Token: token,
		User: model.UserResponse{
			ID:        user.ID,
			Username:  user.Username,
			CreatedAt: user.CreatedAt.In(sgtLocation),
		},
	})
}

// Me handles GET /api/auth/me
func (h *AuthHandler) Me(ctx context.Context, c *app.RequestContext) {
	val, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, map[string]string{
			"error": "unauthorized",
		})
		return
	}

	userID, ok := val.(int64)
	if !ok {
		c.JSON(http.StatusUnauthorized, map[string]string{
			"error": "invalid session",
		})
		return
	}

	user, err := h.Repo.GetUserByID(ctx, userID)
	if err != nil {
		c.JSON(http.StatusNotFound, map[string]string{
			"error": "user not found",
		})
		return
	}

	c.JSON(http.StatusOK, model.UserResponse{
		ID:        user.ID,
		Username:  user.Username,
		CreatedAt: user.CreatedAt.In(sgtLocation),
	})
}
