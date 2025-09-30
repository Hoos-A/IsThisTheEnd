export type RecordingState = "idle" | "recording" | "stopped";

export interface RecorderOptions {
  onChunk: (chunk: ArrayBuffer) => void;
  onStop: () => void;
}

export class AudioRecorder {
  private mediaRecorder?: MediaRecorder;
  private state: RecordingState = "idle";

  constructor(private options: RecorderOptions) {}

  async start() {
    if (this.state === "recording") return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    this.mediaRecorder.addEventListener("dataavailable", async (event) => {
      if (event.data.size > 0) {
        const buffer = await event.data.arrayBuffer();
        this.options.onChunk(buffer);
      }
    });
    this.mediaRecorder.addEventListener("stop", () => {
      this.state = "stopped";
      this.options.onStop();
    });
    this.mediaRecorder.start(500);
    this.state = "recording";
  }

  stop() {
    if (this.state !== "recording" || !this.mediaRecorder) return;
    this.mediaRecorder.stop();
    this.mediaRecorder.stream.getTracks().forEach((track) => track.stop());
  }
}
