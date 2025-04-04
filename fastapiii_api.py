from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from whisper_streaming.whisper_online import WhisperTimestampedASR, OnlineASRProcessor, SAMPLING_RATE
import numpy as np
import uvicorn
import sys
import logging

logging.basicConfig(level=logging.INFO)
asr_backend = WhisperTimestampedASR(
    lan="en",
    modelsize="tiny",
    model_dir=None,
    cache_dir=None,
    logfile=sys.stderr
)

app = FastAPI()

def format_deepgram_response(segments, is_final=False):
    results = []
    for segment in segments:
        print(segment)
        if not isinstance(segment, (dict, str)):
            continue
        if isinstance(segment, str):
            segment = {
                "text": segment,
                "start": 0,
                "end": 0,
                "words": []
            }

        words = []
        print("Segment:", segment)
        for word in segment.get("words", []):
            words.append({
                "word": word.get("word", ""),
                "start": word.get("start", 0),
                "end": word.get("end", 0),
                "confidence": word.get("probability", 0.0)
            })

        start = segment.get("start", 0)
        end = segment.get("end", 0)
        result = {
            "type": "Results",
            "channel_index": [0],
            "duration": end - start,
            "start": start,
            "is_final": is_final,
            "speech_final": is_final,
            "channel": {
                "alternatives": [{
                    "transcript": segment.get("text", ""),
                    "confidence": segment.get("confidence", 0.0),
                    "words": words
                }]
            }
        }
        results.append(result)
    return results

@app.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    asr_processor = None
    try:
        asr_processor = OnlineASRProcessor(
            asr=asr_backend,
            buffer_trimming=("segment", 15),
            logfile=sys.stderr
        )

        while True:
            data = await websocket.receive_bytes()
            audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            asr_processor.insert_audio_chunk(audio)
            segments = asr_processor.process_iter()
            if segments:
                response = format_deepgram_response(segments, is_final=False)
                await websocket.send_json({"results": response})

    except WebSocketDisconnect:
        if asr_processor:
            final_segments = asr_processor.finish()
            if final_segments:
                response = format_deepgram_response(final_segments, is_final=True)
                await websocket.send_json({"results": response})
        logging.info("Client disconnected normally")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        await websocket.close(code=1011)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3004)