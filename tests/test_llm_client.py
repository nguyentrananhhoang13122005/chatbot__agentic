# -*- coding: utf-8 -*-
"""Test circuit breaker model của llm_client (không gọi mạng)."""
import llm_client


def setup_function(_):
    llm_client._cooldown_until.clear()


def test_failed_model_moves_to_end_then_recovers():
    models = ["a", "b", "c"]
    llm_client._record_model_result("a", ok=False, error="rate_limit")
    assert llm_client._order_models(models) == ["b", "c", "a"]
    llm_client._record_model_result("a", ok=True)
    assert llm_client._order_models(models) == ["a", "b", "c"]


def test_all_models_cooling_are_still_tried():
    models = ["a", "b"]
    for m in models:
        llm_client._record_model_result(m, ok=False, error="connection_error")
    assert sorted(llm_client._order_models(models)) == ["a", "b"]


def test_unauthorized_does_not_trip_breaker():
    llm_client._record_model_result("a", ok=False, error="unauthorized")
    assert llm_client._order_models(["a", "b"]) == ["a", "b"]


def test_removed_model_cools_down_longer():
    llm_client._record_model_result("x", ok=False, error="model_unavailable:404")
    llm_client._record_model_result("y", ok=False, error="rate_limit")
    assert llm_client._cooldown_until["x"] > llm_client._cooldown_until["y"]
