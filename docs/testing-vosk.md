# AuraDoc Vosk recording test

This procedure verifies transcription using a real human-recorded statement. Do not type a transcript into the database or workspace; AuraDoc must produce the transcript from the uploaded audio.

## Record the test statement

Record yourself saying:

> According to the agreement, the payment will be completed within 30 days of receiving the invoice.

Save or export the recording as a WAV file with these properties:

- Uncompressed PCM
- Mono channel
- 16-bit samples
- 16 kHz sample rate (8–48 kHz is accepted)
- A few seconds of clear English speech, with little background noise

If the recorder only exports another format, open the recording in an audio editor such as Audacity and export it as **WAV (Signed 16-bit PCM)**, mono, 16 kHz. Do not use an online converter for confidential case audio.

## Run the AuraDoc test

1. Sign in to AuraDoc and open a case that is authorized for this recording.
2. In its investigation workspace, choose the **Recorded statement · WAV** upload control.
3. Select the WAV and choose **Transcribe recording**.
4. Confirm the workspace displays a recording hash and one or more timestamped transcript segments.
5. Compare the displayed segment text with the spoken words. Correctness must be judged against the actual recording; the suggested wording is not a transcript to insert manually.
6. Refresh the case workspace and confirm the recording and transcript segments remain present.

The API accepts WAV only and rejects compressed, non-mono, non-16-bit, unreadable, or out-of-range audio. The local model path is configured in `backend/.env` as `VOSK_MODEL_PATH=./models/vosk-model-small-en-us-0.15`; start FastAPI from the `backend` directory so that relative path resolves as documented.

## Evidence to capture

Record the case and recording identifiers, SHA-256, actual transcript segment text, start/end milliseconds, ASR provider/model, and whether the transcript remained after refresh. Do not publish the audio or transcript outside the authorized case. A transcript is machine-generated evidence for human verification, not proof of what a speaker intended.

No test WAV is committed by this procedure. A generated/synthetic voice fixture must be labeled as synthetic and must never be represented as an interview, deposition, or real case recording.
