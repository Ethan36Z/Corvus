import json
import urllib.request

API_URL = "http:" + chr(47) + chr(47) + "127.0.0.1:8095" + chr(47) + "v1" + chr(47) + "chat" + chr(47) + "completions"

messages = []

print("Small-VRAM Companion — Experiment A")
print("Current-session memory only.")
print("Type /exit to quit.")
print()

while True:
    try:
        user_text = input("You > ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if not user_text:
        continue

    if user_text == "/exit":
        break

    messages.append({
        "role": "user",
        "content": user_text,
    })

    payload = {
        "messages": messages,
        "temperature": 0,
        "top_p": 1.0,
        "seed": 42,
        "max_tokens": 256,
        "chat_template_kwargs": {
            "enable_thinking": False
        }
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            result = json.load(response)
    except Exception as exc:
        messages.pop()
        print(f"\nConnection error: {exc}\n")
        continue

    assistant_text = result["choices"][0]["message"]["content"]

    messages.append({
        "role": "assistant",
        "content": assistant_text,
    })

    print(f"\nAI  > {assistant_text}\n")

print("Session ended. Nothing was saved.")
