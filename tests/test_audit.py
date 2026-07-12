"""Tests for audit logging."""

import json
import os
import tempfile
import pytest
from conservation_enforcer import (
    ConservationEnforcer,
    AuditLog,
    length_budget_policy,
    combined_policy,
)


class TestAuditLog:
    def test_log_creation(self):
        """Audit log creates file and writes entries."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name

        try:
            audit = AuditLog(path)
            entry = audit.log(
                input_text="test question",
                output_text="test response",
                allowed=True,
                cycles=42,
                remaining_budget=950,
                call_count=1,
            )
            assert entry.allowed is True
            assert entry.cycles == 42
            assert os.path.exists(path)

            # Read back
            entries = audit.read_all()
            assert len(entries) == 1
            assert entries[0]["allowed"] is True
            assert entries[0]["cycles"] == 42
        finally:
            os.unlink(path)

    def test_log_hashes_not_raw_content(self):
        """Audit log stores hashes, not raw text."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name

        try:
            audit = AuditLog(path)
            audit.log(
                input_text="secret question",
                output_text="secret response",
                allowed=True,
            )
            with open(path) as f:
                content = f.read()
            assert "secret question" not in content
            assert "secret response" not in content
        finally:
            os.unlink(path)

    def test_multiple_entries(self):
        """Multiple audit entries are logged correctly."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name

        try:
            audit = AuditLog(path)
            for i in range(5):
                audit.log(
                    input_text=f"question {i}",
                    output_text=f"response {i}",
                    allowed=i % 2 == 0,
                    violation_reason=None if i % 2 == 0 else "Test violation",
                    cycles=i * 10,
                )
            entries = audit.read_all()
            assert len(entries) == 5
            assert entries[2]["allowed"] is True
            assert entries[3]["allowed"] is False
        finally:
            os.unlink(path)

    def test_summary_statistics(self):
        """Summary returns correct aggregate stats."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name

        try:
            audit = AuditLog(path)
            audit.log("q1", "r1", True, cycles=10)
            audit.log("q2", "r2", False, violation_reason="Test A", cycles=20)
            audit.log("q3", "r3", True, cycles=15)
            audit.log("q4", "r4", False, violation_reason="Test B", cycles=25)
            audit.log("q5", "r5", False, violation_reason="Test A", cycles=30)

            s = audit.summary()
            assert s["total_calls"] == 5
            assert s["total_blocked"] == 3
            assert s["block_rate"] == 0.6
            assert s["violation_breakdown"]["Test A"] == 2
            assert s["violation_breakdown"]["Test B"] == 1
        finally:
            os.unlink(path)

    def test_empty_summary(self):
        """Empty log should return zeroed summary."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name

        try:
            audit = AuditLog(path)
            s = audit.summary()
            assert s["total_calls"] == 0
            assert s["block_rate"] == 0.0
        finally:
            os.unlink(path)


class TestEnforcerAuditIntegration:
    def test_enforcer_writes_audit_log(self):
        """ConservationEnforcer with enable_audit writes log entries."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name

        try:
            enforcer = ConservationEnforcer(
                length_budget_policy(max_tokens=5),
                budget=5,
                enable_audit=True,
                audit_path=path,
            )
            enforcer.enforce("question", "short answer")
            enforcer.enforce("question", "this is a very long answer that exceeds budget")

            audit = AuditLog(path)
            entries = audit.read_all()
            assert len(entries) == 2
            assert entries[0]["allowed"] is True
            assert entries[1]["allowed"] is False
            assert "input_hash" in entries[0]
            assert "output_hash" in entries[0]
        finally:
            os.unlink(path)
