from modules.verifier import _token_coverage


def test_token_coverage_detects_substantially_supported_excerpt():
    assert _token_coverage("you may terminate an account", "we may terminate an account at any time") >= 0.8


def test_token_coverage_exact_excerpt_is_a_full_match():
    assert _token_coverage("You may terminate an account.", "[Page 2] You may terminate an account.") == 1.0


def test_token_coverage_tolerates_minor_inflection_difference():
    assert _token_coverage("Subscription renews automatically each month", "Subscriptions renew automatically each month") >= 0.9


def test_token_coverage_allows_source_insertions_without_reordering():
    assert _token_coverage("You may cancel subscription", "You may cancel your monthly subscription") == 1.0


def test_token_coverage_rejects_unsupported_excerpt():
    assert _token_coverage("Arbitration applies to every dispute", "We collect account data and retain it securely") < 0.5
