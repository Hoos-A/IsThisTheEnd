export type WsEventHandler = (event: MessageEvent) => void;

export interface ResilientSocketOptions {
  url: string;
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onMessage?: WsEventHandler;
  onError?: (event: Event) => void;
}

export class ResilientWebSocket {
  private socket: WebSocket | null = null;
  private retries = 0;
  private readonly maxRetries = 5;
  private readonly options: ResilientSocketOptions;

  constructor(options: ResilientSocketOptions) {
    this.options = options;
    this.connect();
  }

  private connect() {
    this.socket = new WebSocket(this.options.url);
    this.socket.onopen = () => {
      this.retries = 0;
      this.options.onOpen?.();
    };
    this.socket.onmessage = (event) => this.options.onMessage?.(event);
    this.socket.onclose = (event) => {
      this.options.onClose?.(event);
      if (this.retries < this.maxRetries) {
        const timeout = Math.min(1000 * 2 ** this.retries, 10000);
        this.retries += 1;
        setTimeout(() => this.connect(), timeout);
      }
    };
    this.socket.onerror = (event) => this.options.onError?.(event);
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return;
    }
    this.socket.send(data);
  }

  close() {
    this.socket?.close();
  }
}

export function createResilientWebSocket(options: ResilientSocketOptions) {
  return new ResilientWebSocket(options);
}
