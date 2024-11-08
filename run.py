from app import create_app, socketio

print("Starting application...")
app = create_app()

if __name__ == '__main__':
    socketio.run(app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True,
        use_reloader=False  # Added this
    )