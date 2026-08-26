package middleware

import (
	"os"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/maoxiongkai/screenscout-backend/model"
)

func TestGenerateAndParseToken(t *testing.T) {
	user := &model.User{
		ID:       42,
		Username: "testcinemafan",
	}

	tokenStr, err := GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken failed: %v", err)
	}
	if tokenStr == "" {
		t.Fatal("GenerateToken returned empty token string")
	}

	claims, err := ParseToken(tokenStr)
	if err != nil {
		t.Fatalf("ParseToken failed: %v", err)
	}

	if claims.UserID != 42 {
		t.Errorf("Expected UserID 42, got %d", claims.UserID)
	}
	if claims.Username != "testcinemafan" {
		t.Errorf("Expected Username 'testcinemafan', got '%s'", claims.Username)
	}
	if claims.Issuer != "screenscout" {
		t.Errorf("Expected Issuer 'screenscout', got '%s'", claims.Issuer)
	}
}

func TestParseToken_InvalidSignature(t *testing.T) {
	user := &model.User{
		ID:       10,
		Username: "alice",
	}

	// Create token signed with a different secret
	claims := UserClaims{
		UserID:   user.ID,
		Username: user.Username,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(1 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Issuer:    "screenscout",
		},
	}
	foreignToken := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenStr, err := foreignToken.SignedString([]byte("wrong-secret-key-12345"))
	if err != nil {
		t.Fatalf("Failed to sign foreign token: %v", err)
	}

	_, err = ParseToken(tokenStr)
	if err == nil {
		t.Error("Expected error for token signed with wrong secret, got nil")
	}
}

func TestParseToken_Expired(t *testing.T) {
	// Create an already expired token
	claims := UserClaims{
		UserID:   99,
		Username: "expired_user",
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(-1 * time.Hour)), // 1 hour in the past
			IssuedAt:  jwt.NewNumericDate(time.Now().Add(-2 * time.Hour)),
			Issuer:    "screenscout",
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenStr, err := token.SignedString(jwtSecretKey)
	if err != nil {
		t.Fatalf("Failed to sign expired token: %v", err)
	}

	_, err = ParseToken(tokenStr)
	if err == nil {
		t.Error("Expected error for expired token, got nil")
	}
}

func TestParseToken_Malformed(t *testing.T) {
	testCases := []string{
		"",
		"not-a-jwt",
		"header.payload",
		"invalid.token.signature.extra",
	}

	for _, tc := range testCases {
		_, err := ParseToken(tc)
		if err == nil {
			t.Errorf("Expected error for malformed token '%s', got nil", tc)
		}
	}
}

func TestGetJWTSecret(t *testing.T) {
	origSecret := os.Getenv("JWT_SECRET")
	defer func() {
		if origSecret != "" {
			_ = os.Setenv("JWT_SECRET", origSecret)
		} else {
			_ = os.Unsetenv("JWT_SECRET")
		}
	}()

	_ = os.Unsetenv("JWT_SECRET")
	secretDefault := getJWTSecret()
	if secretDefault == "" {
		t.Error("Default JWT secret should not be empty")
	}

	_ = os.Setenv("JWT_SECRET", "custom-ci-secret")
	secretCustom := getJWTSecret()
	if secretCustom != "custom-ci-secret" {
		t.Errorf("Expected 'custom-ci-secret', got '%s'", secretCustom)
	}
}
