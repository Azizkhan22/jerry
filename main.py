import uvicorn

if __name__ == "__main__":
    # Listens on all interfaces so the same-WiFi/phone access works too
    # (mic recording additionally requires HTTPS for non-localhost origins -
    # see README for the ngrok-based workaround).
    uvicorn.run("web.server:app", host="0.0.0.0", port=8000)
