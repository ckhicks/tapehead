# Tapehead 🎧

**Tapehead** is a lightweight, cloud-native audio processing microservice. It:

- Accepts API calls with FFmpeg instructions and input audio URLs
- Dynamically downloads input files
- Runs complex FFmpeg operations
- Uploads output files to Cloudflare R2 (S3-compatible cloud storage)
- Sends a webhook callback to notify the client when processing is complete

Tapehead runs fully async, inside Docker, designed for scalability and simplicity.
Perfect for dynamic podcast production, audio pipelines, or automated editing tasks.

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/spoolermedia/tapehead.git
cd tapehead
```

---

### 2. Create your `.env` file

Copy the dot-env-sample or create a `.env` file in the root directory with your R2 and bucket settings:

```dotenv
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_ENDPOINT_URL=https://6d10a29f827b44c06b7cda293c83ec60.r2.cloudflarestorage.com
R2_PUBLIC_BASE_URL=https://pub-0ceeaf4ef6c140ae97664c2ff2988776.r2.dev
R2_BUCKET=tapehead
```

Make sure your R2 bucket is **public** or set up pre-signed URLs separately.

---

### 3. Build and start Tapehead with Docker

```bash
docker-compose up --build
```

You should see:

```
Uvicorn running on http://0.0.0.0:8000
```

Tapehead is now ready to accept jobs at `http://localhost:8000/process`.

---

## Testing with Webhook.site (No local server needed)

Because Tapehead uses **background jobs** + **webhook callbacks**, the easiest way to test it is with [https://webhook.site](https://webhook.site).

### Steps:

1. Visit [https://webhook.site](https://webhook.site)
2. It will automatically generate a unique webhook URL for you
   - Example: `https://webhook.site/7ad9e0fa-b97f-446d-975b-93ddb124419e`
3. Copy that URL.

If your client doesn't have a way to receive a webhook, you can also see the URLs in the log:

```
docker-compose logs -f tapehead
```

---

## Example `curl` call

Here’s a full example using your Webhook.site URL:

```bash
curl -X POST http://localhost:8000/process   -H "Content-Type: application/json"   -d '{
    "input_files": {
      "in_1_0": "https://interactive.assets.spooler.fm/system/silence-0.mp3",
      "in_1_1": "https://interactive.assets.spooler.fm/games/ce077ac3-84fe-4be6-8fa7-29e78d79d7cb/40989530-4eba-4765-850e-f2547d6b20fd.mp3",
      "in_1_2": "https://interactive.assets.spooler.fm/games/ce077ac3-84fe-4be6-8fa7-29e78d79d7cb/fe62f58f-699c-4695-aa16-737d222ee4c5.mp3"
    },
    "output_files": {
      "out_1": "output-merged.mp3"
    },
    "ffmpeg_command": "-i {{in_1_0}} -i {{in_1_1}} -i {{in_1_2}} -filter_complex \"[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration=0.5[in_1_0_stereo];[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration=4.583[in_1_1_stereo];[2:a]aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration=7.24[in_1_2_stereo];[in_1_0_stereo][in_1_1_stereo][in_1_2_stereo]concat=n=3:v=0:a=1[in_1];[in_1]channelsplit=channel_layout=stereo[in_0_l][in_0_r];[in_0_l]amix=inputs=1:duration=longest[left];[in_0_r]amix=inputs=1:duration=longest[right];[left][right]amerge=inputs=2[stereo]\" -map \"[stereo]\" -ac 2 {{out_1}}",
    "callback_url": "https://webhook.site/7ad9e0fa-b97f-446d-975b-93ddb124419e"
  }'
```

---

### What Happens:

- You immediately get a response:
  `{ "message": "Job started" }`
- Tapehead runs ffmpeg, uploads the output to Cloudflare R2
- Then Tapehead **POSTs** the final output URL(s) to your `callback_url`
- You'll see the callback hit live inside your [Webhook.site](https://webhook.site) dashboard!

---

## Configuration Notes

- Cloudflare R2 must have public access **enabled** unless you're using pre-signed URLs.
- Only `.mp3` files are assumed right now.
- Errors during download, ffmpeg processing, or uploading are logged to console.

---

## Future Improvements

- `job_id` tracking and job status polling
- Retry logic for failed webhook callbacks
- Pre-signed URLs for private R2 buckets
- Batch processing multiple outputs
- Admin dashboard or logs API

---

# Tapehead lives 🎸
Lightweight, dockerized, async audio processing!
