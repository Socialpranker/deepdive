from runner.qclass import QCLASSES, DEFAULT_QCLASS, normalize_qclass


def test_seventeen_classes_match_dispatch_matrix():
    assert len(QCLASSES) == 17
    assert "market-size" in QCLASSES
    assert "scientific-claim" in QCLASSES
    assert DEFAULT_QCLASS in QCLASSES


def test_normalize_accepts_known_class():
    assert normalize_qclass("pricing") == "pricing"


def test_normalize_is_case_and_space_insensitive():
    assert normalize_qclass("  Market-Size ") == "market-size"


def test_unknown_class_falls_back_to_default_not_crash():
    assert normalize_qclass("шапито") == DEFAULT_QCLASS


def test_empty_falls_back_to_default():
    assert normalize_qclass("") == DEFAULT_QCLASS
