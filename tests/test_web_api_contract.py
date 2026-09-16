import app.playground_api as api


original_process_turn = api.process_turn


def runtime_result(
    *,
    session_id,
    web_mode,
    web_grounding_status,
    web_evidence_status,
):
    return {
        "session_id": session_id,
        "user_message_id": 901,
        "assistant_message_id": 902,
        "attachment_id": None,
        "attachment_status": "NOT_REQUESTED",
        "attachment_error": None,
        "transcription_status": "NOT_REQUESTED",
        "transcription_error": None,
        "transcript_artifact_id": None,
        "transcript": None,
        "web_mode": web_mode,
        "web_grounding_status": (
            web_grounding_status
        ),
        "web_grounding_error": None,
        "web_grounding_selected_result_id": (
            "result_2"
            if web_mode == "on"
            else None
        ),
        "web_evidence_status": (
            web_evidence_status
        ),
        "web_evidence_error": None,
        "web_evidence_refs": (
            ["web_1"]
            if web_mode == "on"
            else []
        ),
        "web_evidence_prompt_chars": (
            123
            if web_mode == "on"
            else 0
        ),
        "web_evidence_persisted_count": (
            1
            if web_mode == "on"
            else 0
        ),
        "recent_message_ids": [],
        "historical_message_ids": [],
        "input_tokens": 42,
        "retrieval_status": "OK",
        "retrieval_error": None,
        "model_status": "OK",
        "dense_status": "OK",
        "persistence_status": "NORMAL",
        "reply": "API reply",
        "error": None,
    }


try:
    #
    # Explicit Web mode must be forwarded into
    # the persistent runtime.
    #
    captured = {}

    def fake_web_process_turn(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return runtime_result(
            session_id=kwargs[
                "session_id"
            ],
            web_mode=kwargs[
                "web_mode"
            ],
            web_grounding_status="READY",
            web_evidence_status="PERSISTED",
        )

    api.process_turn = (
        fake_web_process_turn
    )

    web_response = api.post_chat(
        api.ChatRequest(
            session_id="web-api-test",
            message=(
                "What changed in Python 3.14?"
            ),
            web_mode="on",
        )
    )

    assert (
        captured["session_id"]
        == "web-api-test"
    )

    assert (
        captured["user_content"]
        == "What changed in Python 3.14?"
    )

    assert (
        captured["web_mode"]
        == "on"
    )

    assert (
        web_response["web_mode"]
        == "on"
    )

    assert (
        web_response[
            "web_grounding_status"
        ]
        == "READY"
    )

    assert (
        web_response[
            "web_grounding_selected_result_id"
        ]
        == "result_2"
    )

    assert (
        web_response[
            "web_evidence_status"
        ]
        == "PERSISTED"
    )

    assert (
        web_response[
            "web_evidence_refs"
        ]
        == ["web_1"]
    )

    assert (
        web_response[
            "web_evidence_persisted_count"
        ]
        == 1
    )

    assert (
        web_response["status"][
            "web_grounding"
        ]
        == "READY"
    )

    assert (
        web_response["status"][
            "web_evidence"
        ]
        == "PERSISTED"
    )

    print(
        "WEB API MODE FORWARDING CONTRACT OK"
    )

    print(
        "WEB API OBSERVABILITY CONTRACT OK"
    )


    #
    # Default product-facing request behavior is Web-auto.
    #
    captured = {}

    def fake_off_process_turn(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return runtime_result(
            session_id=kwargs[
                "session_id"
            ],
            web_mode=kwargs[
                "web_mode"
            ],
            web_grounding_status=(
                "NOT_REQUESTED"
            ),
            web_evidence_status=(
                "NOT_REQUESTED"
            ),
        )

    api.process_turn = (
        fake_off_process_turn
    )

    off_response = api.post_chat(
        api.ChatRequest(
            session_id=(
                "web-api-default-auto"
            ),
            message="Hello Corvus",
        )
    )

    assert (
        captured["web_mode"]
        == "auto"
    )

    assert (
        off_response["web_mode"]
        == "auto"
    )

    assert (
        off_response[
            "web_grounding_status"
        ]
        == "NOT_REQUESTED"
    )

    print(
        "WEB API DEFAULT-AUTO PRODUCT CONTRACT OK"
    )


    #
    # Invalid mode must fail before runtime.
    #
    runtime_called = []

    def must_not_run(
        **kwargs,
    ):
        runtime_called.append(
            True
        )
        raise AssertionError(
            "runtime must not run "
            "for invalid web_mode"
        )

    api.process_turn = must_not_run

    invalid_response = (
        api.post_chat(
            api.ChatRequest(
                session_id=(
                    "web-api-invalid"
                ),
                message="Hello",
                web_mode="invalid",
            )
        )
    )

    assert (
        getattr(
            invalid_response,
            "status_code",
            None,
        )
        == 400
    )

    assert runtime_called == []

    print(
        "WEB API INVALID-MODE FAIL-CLOSED CONTRACT OK"
    )

finally:
    api.process_turn = (
        original_process_turn
    )


print(
    "A3_4_WEB_API_ENTRY=PASS"
)
