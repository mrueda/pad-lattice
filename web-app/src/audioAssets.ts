/** WebKit's media player cannot read Tauri's custom protocol directly. */
export class AudioAssets {
  private sources = new Map<string, Promise<string>>();
  private urls = new Set<string>();
  private disposed = false;

  constructor(private bundled: boolean) {}

  resolve(path: string): Promise<string> {
    if (this.disposed) return Promise.reject(new Error('Audio output closed'));
    if (!this.bundled) return Promise.resolve(path);
    let source = this.sources.get(path);
    if (!source) {
      source = fetch(path).then(async (response) => {
        if (!response.ok) throw new Error(`Audio asset unavailable (${response.status})`);
        const blob = await response.blob();
        if (this.disposed) throw new Error('Audio output closed');
        const url = URL.createObjectURL(blob);
        this.urls.add(url);
        return url;
      }).catch((error: unknown) => {
        this.sources.delete(path);
        throw error;
      });
      this.sources.set(path, source);
    }
    return source;
  }

  close() {
    this.disposed = true;
    this.urls.forEach((url) => URL.revokeObjectURL(url));
    this.urls.clear();
    this.sources.clear();
  }
}
