package handler

import (
	"testing"

	"golang.org/x/crypto/bcrypt"
)

func TestPasswordValidation(t *testing.T) {
	if err := validatePassword("Password123!"); err != nil {
		t.Errorf("Password123! should be valid, got %v", err)
	}
	if err := validatePassword("short"); err == nil {
		t.Error("short password should be rejected")
	}
	if err := validatePassword("alllowercase123!"); err == nil {
		t.Error("missing uppercase should be rejected")
	}
}

func TestBcryptHashMatching(t *testing.T) {
	seedHash := "$2a$10$E94AjriKZC2Jq3O/yuoS9eTFYEIqKHHH.umblOjp9WmO7E8oxzoTm"
	if err := bcrypt.CompareHashAndPassword([]byte(seedHash), []byte("Password123!")); err != nil {
		t.Errorf("Seed hash comparison failed for Password123!: %v", err)
	}

	hash, err := bcrypt.GenerateFromPassword([]byte("Password123!"), bcrypt.DefaultCost)
	if err != nil {
		t.Fatalf("GenerateFromPassword failed: %v", err)
	}

	t.Logf("Generated Bcrypt Hash for Password123!: %s", string(hash))

	if err := bcrypt.CompareHashAndPassword(hash, []byte("Password123!")); err != nil {
		t.Errorf("Bcrypt comparison failed: %v", err)
	}
}
