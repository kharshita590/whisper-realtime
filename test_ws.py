import websocket
import threading
import time
import pyaudio

CHUNK = 1600  
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

def on_message(ws, message):
    print("Received:", message)

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("### Closed ###")

def on_open(ws):
    def stream_microphone():
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
        
        try:
            while ws.sock and ws.sock.connected:
                data = stream.read(CHUNK)
                ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
                time.sleep(0.09) 
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
    threading.Thread(target=stream_microphone).start()

if __name__ == "__main__":
    ws_url = "ws://localhost:3004/listen"
    ws = websocket.WebSocketApp(ws_url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    ws.run_forever(ping_interval=10, ping_timeout=5)