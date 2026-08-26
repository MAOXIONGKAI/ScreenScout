package repo

import (
	"errors"
	"testing"
)

func TestSubscriptionRepoErrors(t *testing.T) {
	if ErrSubscriptionNotFound == nil {
		t.Error("ErrSubscriptionNotFound should be defined")
	}
	if ErrChannelNotFound == nil {
		t.Error("ErrChannelNotFound should be defined")
	}
	if ErrMaxActiveSubscriptionsReached == nil {
		t.Error("ErrMaxActiveSubscriptionsReached should be defined")
	}

	if !errors.Is(ErrMaxActiveSubscriptionsReached, ErrMaxActiveSubscriptionsReached) {
		t.Error("errors.Is should match ErrMaxActiveSubscriptionsReached")
	}

	expectedMsg := "maximum active monitoring limit reached (10 tasks)"
	if ErrMaxActiveSubscriptionsReached.Error() != expectedMsg {
		t.Errorf("Expected error message '%s', got '%s'", expectedMsg, ErrMaxActiveSubscriptionsReached.Error())
	}
}
