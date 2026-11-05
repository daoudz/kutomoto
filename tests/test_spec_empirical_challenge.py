"""
Empirical Adversarial Stress Harness & Edge Case Suite for kutomoto Specification.
Copyrights reserved to 90Studio
"""
from jsonschema import Draft202012Validator

def test_unicode_and_special_character_payloads(compiler_func, workflow_schema):
    """
    Stress-tests compiler with international enterprise character sets (Arabic, CJK, Cyrillic, Currency, Emojis).
    """
    layout = {
        "canvas": {"width": 1920, "height": 1080},
        "target": {"type": "web_browser", "window_title_pattern": "International KYC Portal"},
        "boxes": [
            {
                "name": "arabic_name",
                "label": "الاسم الكامل",
                "rect": {"x": 100, "y": 100, "width": 250, "height": 36},
                "sequence_index": 1,
                "field_type": "text",
                "value_config": {
                    "source_type": "static",
                    "static_value": "محمد عبد الله",
                    "is_secret": False,
                    "clear_before_type": True
                },
                "navigation": "tab"
            },
            {
                "name": "cjk_address",
                "label": "東京都千代田区大手町",
                "rect": {"x": 100, "y": 160, "width": 300, "height": 36},
                "sequence_index": 2,
                "field_type": "text",
                "value_config": {
                    "source_type": "static",
                    "static_value": "1-1-1 Otemachi 〒100-0004",
                    "is_secret": False,
                    "clear_before_type": True
                },
                "navigation": "tab"
            },
            {
                "name": "currency_transfer",
                "label": "Transfer Amount € & £",
                "rect": {"x": 100, "y": 220, "width": 200, "height": 36},
                "sequence_index": 3,
                "field_type": "text",
                "value_config": {
                    "source_type": "static",
                    "static_value": "€1,250,000.50 / £850,000.00",
                    "is_secret": False,
                    "clear_before_type": True
                },
                "navigation": "none"
            }
        ]
    }
    wf = compiler_func(layout)
    validator = Draft202012Validator(workflow_schema)
    errors = list(validator.iter_errors(wf))
    assert not errors, f"Unicode workflow failed validation: {[e.message for e in errors]}"
    
    # Check payload fidelity
    type_steps = [s for s in wf["steps"] if s["action_type"] == "type_text"]
    assert type_steps[0]["parameters"]["text"] == "محمد عبد الله"
    assert type_steps[1]["parameters"]["text"] == "1-1-1 Otemachi 〒100-0004"
    assert type_steps[2]["parameters"]["text"] == "€1,250,000.50 / £850,000.00"

def test_variable_and_runtime_prompt_bindings(compiler_func, workflow_schema):
    """
    Validates dynamic value_config sources: variable, runtime_prompt, and generated patterns.
    """
    layout = {
        "canvas": {"width": 1000, "height": 800},
        "target": {"type": "web_browser", "window_title_pattern": "Dynamic Binding Test"},
        "boxes": [
            {
                "name": "var_field",
                "label": "IBAN Account",
                "rect": {"x": 100, "y": 100, "width": 200, "height": 30},
                "sequence_index": 1,
                "field_type": "text",
                "value_config": {
                    "source_type": "variable",
                    "variable_name": "target_iban",
                    "is_secret": False,
                    "clear_before_type": True
                },
                "navigation": "tab"
            },
            {
                "name": "prompt_field",
                "label": "OTP Verification Code",
                "rect": {"x": 100, "y": 150, "width": 150, "height": 30},
                "sequence_index": 2,
                "field_type": "text",
                "value_config": {
                    "source_type": "runtime_prompt",
                    "variable_name": "sms_otp",
                    "is_secret": True,
                    "clear_before_type": True
                },
                "navigation": "tab"
            },
            {
                "name": "generated_field",
                "label": "Audit Trace ID",
                "rect": {"x": 100, "y": 200, "width": 200, "height": 30},
                "sequence_index": 3,
                "field_type": "text",
                "value_config": {
                    "source_type": "generated",
                    "generator_pattern": "uuid4",
                    "is_secret": False,
                    "clear_before_type": True
                },
                "navigation": "enter"
            }
        ]
    }
    wf = compiler_func(layout)
    validator = Draft202012Validator(workflow_schema)
    errors = list(validator.iter_errors(wf))
    assert not errors, f"Dynamic workflow failed validation: {[e.message for e in errors]}"

    # Verify prompt step was inserted
    prompt_steps = [s for s in wf["steps"] if s["action_type"] == "prompt_user_input"]
    assert len(prompt_steps) == 1
    assert prompt_steps[0]["parameters"]["variable_name"] == "sms_otp"
    assert prompt_steps[0]["parameters"]["is_password"] is True

    # Verify typing step references
    type_steps = [s for s in wf["steps"] if s["action_type"] == "type_text"]
    assert type_steps[0]["parameters"]["text"] == "{{target_iban}}"
    assert type_steps[1]["parameters"]["text"] == "{{sms_otp}}"
    assert type_steps[2]["parameters"]["text"] == "{{$uuid4}}"

def test_duplicate_sequence_indices_stable_order(compiler_func):
    """
    Tests behavior when multiple boxes share the identical sequence index (Edge Case E12).
    """
    layout = {
        "canvas": {"width": 1000, "height": 800},
        "target": {"window_title_pattern": "Dup Index Test"},
        "boxes": [
            {"name": "box_2a", "rect": {"x": 100, "y": 100, "width": 100, "height": 30}, "sequence_index": 2, "field_type": "text"},
            {"name": "box_1",  "rect": {"x": 100, "y": 50,  "width": 100, "height": 30}, "sequence_index": 1, "field_type": "text"},
            {"name": "box_2b", "rect": {"x": 100, "y": 150, "width": 100, "height": 30}, "sequence_index": 2, "field_type": "text"}
        ]
    }
    wf = compiler_func(layout)
    type_labels = [s["label"] for s in wf["steps"] if s["action_type"] == "type_text"]
    # Python stable sort preserves box_2a before box_2b
    assert type_labels == ["Type into [box_1]", "Type into [box_2a]", "Type into [box_2b]"]

def test_textarea_and_number_field_types(compiler_func, workflow_schema):
    """
    Tests textarea and number field types are correctly processed by the text pipeline.
    """
    layout = {
        "canvas": {"width": 1024, "height": 768},
        "target": {"type": "web_browser", "window_title_pattern": "Types Test"},
        "boxes": [
            {
                "name": "remarks",
                "label": "Loan Underwriting Remarks",
                "rect": {"x": 50, "y": 50, "width": 400, "height": 120},
                "sequence_index": 1,
                "field_type": "textarea",
                "value_config": {"source_type": "static", "static_value": "Approved under tier 1 facility.\nCollateral inspected.", "is_secret": False, "clear_before_type": True},
                "navigation": "tab"
            },
            {
                "name": "credit_score",
                "label": "FICO Score",
                "rect": {"x": 50, "y": 200, "width": 120, "height": 30},
                "sequence_index": 2,
                "field_type": "number",
                "value_config": {"source_type": "static", "static_value": "785", "is_secret": False, "clear_before_type": True},
                "navigation": "none"
            }
        ]
    }
    wf = compiler_func(layout)
    validator = Draft202012Validator(workflow_schema)
    errors = list(validator.iter_errors(wf))
    assert not errors, f"Textarea/number workflow failed schema validation: {[e.message for e in errors]}"
