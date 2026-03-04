"""Tests for event state machine transitions."""
import pytest

from app.models.event import EventState


class TestValidTransitions:
    """Test that valid state transitions are accepted."""

    def test_pending_to_delivering(self):
        assert EventState.can_transition(EventState.PENDING, EventState.DELIVERING) is True

    def test_delivering_to_delivered(self):
        assert EventState.can_transition(EventState.DELIVERING, EventState.DELIVERED) is True

    def test_delivering_to_retrying(self):
        assert EventState.can_transition(EventState.DELIVERING, EventState.RETRYING) is True

    def test_delivering_to_failed(self):
        assert EventState.can_transition(EventState.DELIVERING, EventState.FAILED) is True

    def test_retrying_to_delivering(self):
        assert EventState.can_transition(EventState.RETRYING, EventState.DELIVERING) is True


class TestInvalidTransitions:
    """Test that invalid state transitions are rejected."""

    def test_pending_to_delivered_not_allowed(self):
        """Cannot skip directly from PENDING to DELIVERED."""
        assert EventState.can_transition(EventState.PENDING, EventState.DELIVERED) is False

    def test_pending_to_failed_not_allowed(self):
        """Cannot skip directly from PENDING to FAILED."""
        assert EventState.can_transition(EventState.PENDING, EventState.FAILED) is False

    def test_pending_to_retrying_not_allowed(self):
        """Cannot skip directly from PENDING to RETRYING."""
        assert EventState.can_transition(EventState.PENDING, EventState.RETRYING) is False

    def test_delivered_to_anything_not_allowed(self):
        """DELIVERED is a terminal state — no transitions out."""
        for target in [EventState.PENDING, EventState.DELIVERING, EventState.RETRYING, EventState.FAILED]:
            assert EventState.can_transition(EventState.DELIVERED, target) is False

    def test_failed_to_anything_not_allowed(self):
        """FAILED is a terminal state — no transitions out."""
        for target in [EventState.PENDING, EventState.DELIVERING, EventState.RETRYING, EventState.DELIVERED]:
            assert EventState.can_transition(EventState.FAILED, target) is False

    def test_retrying_to_delivered_not_allowed(self):
        """Cannot go from RETRYING directly to DELIVERED; must go through DELIVERING."""
        assert EventState.can_transition(EventState.RETRYING, EventState.DELIVERED) is False

    def test_retrying_to_failed_not_allowed(self):
        """Cannot go from RETRYING directly to FAILED; must go through DELIVERING."""
        assert EventState.can_transition(EventState.RETRYING, EventState.FAILED) is False

    def test_self_transition_not_allowed(self):
        """No state should transition to itself."""
        for state in [EventState.PENDING, EventState.DELIVERING, EventState.DELIVERED,
                      EventState.RETRYING, EventState.FAILED]:
            assert EventState.can_transition(state, state) is False


class TestTerminalStates:
    """Verify terminal state properties."""

    def test_delivered_is_terminal(self):
        """DELIVERED should have no valid outbound transitions."""
        assert EventState.DELIVERED not in EventState.VALID_TRANSITIONS

    def test_failed_is_terminal(self):
        """FAILED should have no valid outbound transitions."""
        assert EventState.FAILED not in EventState.VALID_TRANSITIONS


class TestStateValues:
    """Verify state string values match expected schema."""

    def test_pending_value(self):
        assert EventState.PENDING == "PENDING"

    def test_delivering_value(self):
        assert EventState.DELIVERING == "DELIVERING"

    def test_delivered_value(self):
        assert EventState.DELIVERED == "DELIVERED"

    def test_retrying_value(self):
        assert EventState.RETRYING == "RETRYING"

    def test_failed_value(self):
        assert EventState.FAILED == "FAILED"


class TestFullLifecycle:
    """Test complete event lifecycle paths."""

    def test_happy_path(self):
        """PENDING → DELIVERING → DELIVERED."""
        states = [EventState.PENDING, EventState.DELIVERING, EventState.DELIVERED]
        for i in range(len(states) - 1):
            assert EventState.can_transition(states[i], states[i + 1]) is True

    def test_retry_path(self):
        """PENDING → DELIVERING → RETRYING → DELIVERING → DELIVERED."""
        states = [
            EventState.PENDING,
            EventState.DELIVERING,
            EventState.RETRYING,
            EventState.DELIVERING,
            EventState.DELIVERED,
        ]
        for i in range(len(states) - 1):
            assert EventState.can_transition(states[i], states[i + 1]) is True

    def test_failure_path(self):
        """PENDING → DELIVERING → FAILED."""
        states = [EventState.PENDING, EventState.DELIVERING, EventState.FAILED]
        for i in range(len(states) - 1):
            assert EventState.can_transition(states[i], states[i + 1]) is True

    def test_retry_then_failure_path(self):
        """PENDING → DELIVERING → RETRYING → DELIVERING → FAILED."""
        states = [
            EventState.PENDING,
            EventState.DELIVERING,
            EventState.RETRYING,
            EventState.DELIVERING,
            EventState.FAILED,
        ]
        for i in range(len(states) - 1):
            assert EventState.can_transition(states[i], states[i + 1]) is True
