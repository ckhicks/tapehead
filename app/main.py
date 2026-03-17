import boto3
import subprocess
import tempfile
import uuid
import os
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from botocore.client import Config

app = FastAPI()

class FFmpegRequest(BaseModel):
    input_files: Dict[str, str]
    output_files: Dict[str, str]
    ffmpeg_command: str
    callback_url: Optional[str] = None

def process_audio_job(request: FFmpegRequest):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download input files
        local_inputs = {}
        for key, url in request.input_files.items():
            local_path = os.path.join(tmpdir, f"{key}.mp3")
            r = requests.get(url)
            with open(local_path, "wb") as f:
                f.write(r.content)
            local_inputs[key] = local_path

        # Replace input/output placeholders
        command = f"ffmpeg {request.ffmpeg_command}"
        for key, path in local_inputs.items():
            command = command.replace(f"{{{{{key}}}}}", f'"{path}"')

        output_paths = {}
        for key, filename in request.output_files.items():
            output_path = os.path.join(tmpdir, filename)
            output_paths[key] = output_path
            command = command.replace(f"{{{{{key}}}}}", f'"{output_path}"')

        print("Resolved command string:", flush=True)
        print(command, flush=True)

        result = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("ffmpeg error:", result.stderr, flush=True)
            return

        print("ffmpeg output:", result.stdout, flush=True)

        # Upload to R2
        session = boto3.session.Session()
        s3 = session.client(
            service_name="s3",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            endpoint_url=os.environ["R2_ENDPOINT_URL"],
            config=Config(signature_version="s3v4"),
        )

        uploaded_urls = {}
        for key, local_path in output_paths.items():
            object_key = f"{uuid.uuid4()}/{os.path.basename(local_path)}"
            s3.upload_file(local_path, os.environ["R2_BUCKET"], object_key)
            public_url = f"{os.environ['R2_PUBLIC_BASE_URL'].rstrip('/')}/{object_key}"
            uploaded_urls[key] = public_url
            print(f"Uploaded {key}: {public_url}", flush=True)

        # Webhook callback
        if request.callback_url:
            try:
                requests.post(
                    request.callback_url,
                    json={
                        "message": "FFmpeg process completed",
                        "files": uploaded_urls
                    },
                    timeout=10
                )
                print(f"Callback sent to {request.callback_url}", flush=True)
            except Exception as e:
                print(f"Failed to send callback: {e}", flush=True)

@app.post("/process")
async def process_ffmpeg(request: FFmpegRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_audio_job, request)
    return {"message": "Job started"}

@app.get("/")
async def root_deny():
    raise HTTPException(status_code=401, detail="Go Away")
