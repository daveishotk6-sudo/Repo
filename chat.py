from flask import Flask, request, jsonify
import json
import os
import requests

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")

# Retrieve API key securely from environment variables, or fallback to key if defined
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "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")


def get_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")
    model = data.get("model", "meta-llama/llama-3.1-8b-instruct")

    if not user_message:
        return jsonify({"error": "no 'message' field received in request body"}), 400
    if not OPENROUTER_KEY:
        return jsonify({"error": "OPENROUTER_KEY is not set on the server"}), 500

    history = get_history()
    history.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": model, "messages": history},
            timeout=30,
        )
        result = response.json()
        ai_reply = result["choices"][0]["message"]["content"]
    except Exception as e:
        return jsonify({
            "error": f"OpenRouter call failed: {str(e)}",
            "raw": result if "result" in locals() else None
        }), 502

    history.append({"role": "assistant", "content": ai_reply})

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

    return jsonify({"reply": ai_reply})


@app.route("/reset", methods=["POST"])
def reset():
    """Wipe the conversation — call this when you want a fresh chat."""
    with open(HISTORY_FILE, "w") as f:
        json.dump([], f)
    return jsonify({"status": "history cleared"})


if __name__ == "__main__":
    # Dynamically bind to the PORT assigned by hosting platforms
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)