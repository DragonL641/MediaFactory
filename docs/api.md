# MediaFactory API Documentation

## Overview

MediaFactory provides a RESTful API server built with FastAPI, enabling programmatic access to all processing capabilities. The API server runs on `http://127.0.0.1:8765` by default.

## Base URL

```
http://127.0.0.1:8765/api
```

## Authentication

Currently, the API is designed for local use only (bound to `127.0.0.1`). No authentication is required.

---

## Endpoints

### Health Check

#### `GET /health`

Check if the API server is running.

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Processing API

### Start Subtitle Generation Task

#### `POST /api/processing/subtitle`

Start a subtitle generation task.

**Request Body:**
```json
{
  "video_path": "/path/to/video.mp4",
  "source_lang": "auto",
  "target_lang": "zh",
  "use_llm": false,
  "output_format": "srt"
}
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "Task created successfully"
}
```

### Extract Audio

#### `POST /api/processing/audio`

Extract audio from a video file.

**Request Body:**
```json
{
  "video_path": "/path/to/video.mp4"
}
```

### Transcribe Audio

#### `POST /api/processing/transcribe`

Transcribe audio to text using Faster Whisper.

**Request Body:**
```json
{
  "audio_path": "/path/to/audio.wav",
  "language": "auto"
}
```

### Translate Subtitles

#### `POST /api/processing/translate`

Translate subtitles to target language.

**Request Body:**
```json
{
  "srt_path": "/path/to/subtitles.srt",
  "target_lang": "zh",
  "use_llm": false
}
```

### Enhance Video

#### `POST /api/processing/enhance`

Enhance video quality (super-resolution, denoise).

**Request Body:**
```json
{
  "video_path": "/path/to/video.mp4",
  "scale": 2,
  "denoise": true
}
```

### Get Task Status

#### `GET /api/processing/status/{task_id}`

Get the current status of a task.

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "running",
  "progress": 45,
  "stage": "transcription",
  "message": "Transcribing audio..."
}
```

### Cancel Task

#### `POST /api/processing/cancel/{task_id}`

Cancel a running task.

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "cancelled",
  "message": "Task cancelled successfully"
}
```

### Get All Tasks

#### `GET /api/processing/tasks`

Get list of all tasks.

**Response:**
```json
[
  {
    "task_id": "uuid-1",
    "status": "completed",
    "progress": 100
  },
  {
    "task_id": "uuid-2",
    "status": "running",
    "progress": 50
  }
]
```

### Delete Task

#### `DELETE /api/processing/tasks/{task_id}`

Remove a task from the list.

---

## Models API

### Get Model Status

#### `GET /api/models/status`

Get status of all models (Whisper, Translation, LLM).

**Response:**
```json
{
  "whisper": {
    "available": true,
    "name": "large-v3"
  },
  "translation": {
    "models": [
      {
        "id": "google/madlad400-3b-mt",
        "name": "MADLAD-400 3B",
        "tier": "standard",
        "downloaded": true
      }
    ]
  },
  "llm": {
    "available": true,
    "current_preset": "openai"
  }
}
```

### Download Model

#### `POST /api/models/download/{model_id}`

Start downloading a model.

### Delete Model

#### `DELETE /api/models/{model_id}`

Delete a downloaded model.

### Test LLM Connection

#### `POST /api/models/llm/test`

Test connection to LLM API.

**Request Body:**
```json
{
  "preset": "openai"
}
```

**Response:**
```json
{
  "success": true,
  "latency_ms": 250
}
```

### Test All LLM Presets

#### `POST /api/models/llm/test-all`

Test all configured LLM presets.

---

## Config API

### Get Full Configuration

#### `GET /api/config/`

Get the complete application configuration.

**Response:**
```json
{
  "whisper": {
    "beam_size": 5,
    "vad_filter": true,
    "vad_threshold": 0.5
  },
  "llm_api": {
    "current_preset": "openai",
    "timeout": 60,
    "max_retries": 3
  }
}
```

### Get Config Section

#### `GET /api/config/{section}`

Get a specific configuration section.

### Update Configuration

#### `PUT /api/config/`

Update configuration (partial update supported).

**Request Body:**
```json
{
  "whisper": {
    "beam_size": 7
  }
}
```

### Save Configuration

#### `POST /api/config/save`

Save current configuration to disk.

### Reload Configuration

#### `POST /api/config/reload`

Reload configuration from disk.

---

## WebSocket API

### Connect

Connect to `ws://127.0.0.1:8765/ws` for real-time progress updates.

### Subscribe to Task

Send a message to subscribe to task progress:

```json
{
  "type": "subscribe",
  "task_id": "uuid-string"
}
```

### Progress Messages

Receive progress updates:

```json
{
  "type": "progress",
  "task_id": "uuid-string",
  "data": {
    "stage": "transcription",
    "progress": 45,
    "message": "Transcribing audio..."
  }
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (task or resource doesn't exist)
- `500` - Internal Server Error

---

## Example Usage

### Python

```python
import requests

BASE_URL = "http://127.0.0.1:8765/api"

# Create subtitle task
response = requests.post(f"{BASE_URL}/processing/subtitle", json={
    "video_path": "/path/to/video.mp4",
    "source_lang": "auto",
    "target_lang": "zh",
    "use_llm": False,
    "output_format": "srt"
})
task_id = response.json()["task_id"]

# Poll for status
import time
while True:
    status = requests.get(f"{BASE_URL}/processing/status/{task_id}").json()
    print(f"Progress: {status['progress']}% - {status['message']}")
    if status["status"] in ["completed", "failed", "cancelled"]:
        break
    time.sleep(2)
```

### JavaScript

```javascript
const BASE_URL = "http://127.0.0.1:8765/api";

// Create task
const response = await fetch(`${BASE_URL}/processing/subtitle`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    video_path: "/path/to/video.mp4",
    source_lang: "auto",
    target_lang: "zh",
  }),
});
const { task_id } = await response.json();

// WebSocket for progress
const ws = new WebSocket("ws://127.0.0.1:8765/ws");
ws.onopen = () => {
  ws.send(JSON.stringify({ type: "subscribe", task_id }));
};
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.data.progress}%`);
};
```
