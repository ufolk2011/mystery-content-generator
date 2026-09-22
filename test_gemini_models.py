from gemini_models import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_MODELS,
    resolve_gemini_model,
)


def test_default_is_gemini_36_flash():
    assert DEFAULT_GEMINI_MODEL == "gemini-3.6-flash"
    assert DEFAULT_GEMINI_MODEL in GEMINI_MODELS
    assert "gemini-2.5-flash" not in GEMINI_MODELS


def test_empty_and_unknown_fall_back_to_default():
    assert resolve_gemini_model("") == DEFAULT_GEMINI_MODEL
    assert resolve_gemini_model(None) == DEFAULT_GEMINI_MODEL
    assert resolve_gemini_model("not-a-real-model") == DEFAULT_GEMINI_MODEL


def test_deprecated_flash_models_are_remapped():
    assert resolve_gemini_model("gemini-2.5-flash") == "gemini-3.6-flash"
    assert resolve_gemini_model("models/gemini-2.5-flash") == "gemini-3.6-flash"
    assert resolve_gemini_model("gemini-2.0-flash") == "gemini-3.6-flash"
    assert resolve_gemini_model("gemini-2.5-flash-lite") == "gemini-3.5-flash-lite"


def test_current_models_pass_through():
    for model in GEMINI_MODELS:
        assert resolve_gemini_model(model) == model
        assert resolve_gemini_model(f"models/{model}") == model
