# macOS Installer Notes

macOS app packaging is planned but not implemented yet.

The intended experience:

1. User downloads a `.pkg` or `.app`.
2. Installer installs News Talent Monitor+ as a normal macOS app.
3. First launch checks for the NDI runtime.
4. If NDI is missing, the app points the user to the official NDI runtime/SDK download.
5. The app does not bundle the NDI SDK unless the NDI license explicitly allows that distribution path.

NDI runtime check:

```bash
python3 tools/ndi/check_ndi_runtime.py
```
