import argparse

from app.conversation_runtime import process_turn
from app.runtime_lifecycle import recover_dense_tail


DEFAULT_SESSION_ID = "default"
def print_recovery_status(result):
    print(
        "Dense recovery:",
        result["status"],
        f"(batches={result['batches']}, "
        f"indexed={result['indexed']}, "
        f"progress={result['progress_after']})",
    )

    if result["error"]:
        print(
            "Dense recovery warning:",
            result["error"],
        )

    if result["status"] == "BOUNDED":
        print(
            "Dense recovery reached the startup batch limit; "
            "remaining backlog can continue on a later startup."
        )


def print_turn_inspection(result):
    print(
        "[turn]",
        f"user=#{result['user_message_id']}",
        f"assistant=#{result['assistant_message_id']}",
        f"recent={result['recent_message_ids']}",
        f"history={result['historical_message_ids']}",
        f"tokens={result['input_tokens']}",
    )

    print(
        "[state]",
        f"retrieval={result['retrieval_status']}",
        f"model={result['model_status']}",
        f"persistence={result['persistence_status']}",
        f"dense={result['dense_status']}",
    )

    if result["retrieval_error"]:
        print(
            "[retrieval warning]",
            result["retrieval_error"],
        )

    if result["error"]:
        print(
            "[turn warning]",
            result["error"],
        )


def run_chat(session_id):
    recovery = recover_dense_tail()
    print_recovery_status(
        recovery
    )

    print()
    print(
        f"Corvus persistent chat — session={session_id!r}"
    )
    print("Type /exit to quit.")
    print()

    while True:
        try:
            user_content = input(
                "You > "
            )
        except (EOFError, KeyboardInterrupt):
            print()
            print("Session ended.")
            break

        if user_content.strip() == "/exit":
            print("Session ended.")
            break

        if not user_content.strip():
            continue

        try:
            result = process_turn(
                session_id=session_id,
                user_content=user_content,
            )
        except Exception as exc:
            print(
                "Persistence failure:",
                str(exc),
            )
            print(
                "The user message was not accepted as "
                "canonical evidence."
            )
            print()
            continue

        if (
            result["assistant_message_id"]
            is not None
        ):
            print(
                "Corvus >",
                result["reply"],
            )
        elif (
            result["persistence_status"]
            == "ASSISTANT_PERSISTENCE_FAILED"
            and result["reply"]
        ):
            print(
                "Corvus [NOT PERSISTED] >",
                result["reply"],
            )
        else:
            print(
                "Corvus could not complete this turn."
            )

        print_turn_inspection(
            result
        )
        print()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Corvus Stage A1 persistent conversation CLI"
        )
    )

    parser.add_argument(
        "--session",
        default=DEFAULT_SESSION_ID,
        help=(
            "Stable conversation session ID "
            f"(default: {DEFAULT_SESSION_ID})"
        ),
    )

    args = parser.parse_args()

    session_id = args.session.strip()

    if not session_id:
        parser.error(
            "--session must not be empty"
        )

    run_chat(
        session_id
    )


if __name__ == "__main__":
    main()
