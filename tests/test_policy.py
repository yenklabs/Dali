"""Tests for policy versioning — stamping, cross-version refusal."""

import pytest

from corpus.policy import (
    POLICY_VERSION,
    PolicyVersion,
    assert_same_version_or_raise,
    is_same_version,
)


class TestPolicyVersion:
    def test_as_string_contains_all_sub_versions(self):
        pv = POLICY_VERSION.as_string()
        for sub in ("taxonomy=", "rubric=", "scoring=", "normalization=", "schema="):
            assert sub in pv, f"expected {sub!r} in policy version string"

    def test_as_string_semicolon_separated(self):
        pv = POLICY_VERSION.as_string()
        parts = pv.split(";")
        assert len(parts) == 5

    def test_frozen_dataclass(self):
        with pytest.raises(Exception):
            POLICY_VERSION.taxonomy = "9.9.9"

    def test_current_version_is_2_0_0(self):
        assert POLICY_VERSION.taxonomy == "2.0.0"
        assert POLICY_VERSION.rubric == "1.0.0"
        assert POLICY_VERSION.scoring == "1.0.0"
        assert POLICY_VERSION.normalization == "1.0.0"
        assert POLICY_VERSION.schema == "1.0.0"


class TestIsSameVersion:
    def test_same_is_same(self):
        pv = POLICY_VERSION.as_string()
        assert is_same_version(pv, pv) is True

    def test_different_is_not_same(self):
        pv1 = POLICY_VERSION.as_string()
        pv2 = "taxonomy=3.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0"
        assert is_same_version(pv1, pv2) is False


class TestAssertSameVersionOrRaise:
    def test_single_version_passes(self):
        pv = POLICY_VERSION.as_string()
        assert_same_version_or_raise([pv, pv, pv], allow_cross=False)

    def test_empty_list_passes(self):
        assert_same_version_or_raise([], allow_cross=False)

    def test_mixed_versions_raises_without_flag(self):
        pv1 = POLICY_VERSION.as_string()
        pv2 = "taxonomy=3.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0"
        with pytest.raises(ValueError, match="POLICY_VERSION"):
            assert_same_version_or_raise([pv1, pv2], allow_cross=False)

    def test_mixed_versions_allowed_with_flag(self):
        pv1 = POLICY_VERSION.as_string()
        pv2 = "taxonomy=3.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0"
        assert_same_version_or_raise([pv1, pv2], allow_cross=True)  # must not raise

    def test_error_message_mentions_count(self):
        pv1 = POLICY_VERSION.as_string()
        pv2 = "taxonomy=3.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0"
        with pytest.raises(ValueError) as exc_info:
            assert_same_version_or_raise([pv1, pv2], allow_cross=False)
        assert "2" in str(exc_info.value)
