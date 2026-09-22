#!/usr/bin/env python3
import argparse
import json
import os
import socket
import sys
import time

MODEL_REPOS = {
    "english": "convaiinnovations/laya",
    "multilingual": "convaiinnovations/laya-multilingual",
    "typed-decisions": "convaiinnovations/laya-typed-decisions",
}

HEAD_MAX_LEN = {"english": 192, "multilingual": 256, "typed-decisions": 256}
STATE_MAX_LEN = {"english": 512, "multilingual": 1024, "typed-decisions": 1024}


def log(message):
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def load_agent(model, device):
    import laya

    repo = MODEL_REPOS[model]
    started = time.monotonic()
    agent = laya.load(repo, device=device)
    log("loaded %s in %.1fs" % (repo, time.monotonic() - started))
    return agent


def answer(agent, payload, default_model):
    model = payload.get("model") or default_model
    if model not in MODEL_REPOS:
        raise ValueError("unknown model %r" % model)
    state = payload.get("state")
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise ValueError("questions must be a non-empty object")
    if state is None or state == "":
        raise ValueError("state is required")
    started = time.monotonic()
    result = agent.predict(state, questions)
    return {
        "answers": result.get("answers", {}),
        "usage": result.get("usage", {}),
        "provider": "laya",
        "model": model,
        "head_max_len": HEAD_MAX_LEN[model],
        "state_max_len": STATE_MAX_LEN[model],
        "elapsed_ms": round((time.monotonic() - started) * 1000),
    }


def serve(sock_path, model, device):
    agent = load_agent(model, device)
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    os.chmod(sock_path, 0o600)
    server.listen(16)
    log("READY %s" % sock_path)
    try:
        while True:
            conn, _ = server.accept()
            with conn, conn.makefile("rwb") as stream:
                for raw in stream:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        payload = json.loads(raw)
                    except ValueError as error:
                        stream.write(
                            (json.dumps({"error": "bad json: %s" % error}) + "\n").encode()
                        )
                        stream.flush()
                        continue
                    if payload.get("op") == "ping":
                        stream.write(
                            (
                                json.dumps(
                                    {"ok": True, "model": model, "device": device}
                                )
                                + "\n"
                            ).encode()
                        )
                        stream.flush()
                        continue
                    if payload.get("op") == "stop":
                        stream.write((json.dumps({"ok": True}) + "\n").encode())
                        stream.flush()
                        return
                    try:
                        reply = answer(agent, payload, model)
                    except Exception as error:
                        reply = {"error": "%s: %s" % (type(error).__name__, error)}
                    stream.write((json.dumps(reply) + "\n").encode())
                    stream.flush()
    finally:
        server.close()
        if os.path.exists(sock_path):
            os.unlink(sock_path)


def main():
    parser = argparse.ArgumentParser(prog="decide_sidecar")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--model", default="multilingual", choices=sorted(MODEL_REPOS))
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    try:
        serve(args.socket, args.model, args.device)
    except ImportError as error:
        log("laya is not installed in this interpreter: %s" % error)
        sys.exit(3)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
