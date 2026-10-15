from __future__ import annotations
import base64
import importlib
import io
from typing import Any

def _load_qr_runtime(module_loader: Any = None) -> Any:
    loader = module_loader or importlib.import_module
    try:
        return loader("qrcode")
    except Exception:
        raise RuntimeError(
            "SECURE_REVIEW_RUNTIME_REQUIRED: install qrcode==7.4.2 before remote review"
        ) from None


def _render_pairing_qr(remote_url: str, module_loader: Any = None) -> bytes:
    """Render the secret-bearing QR in memory; never write it to the bundle."""
    try:
        qrcode = _load_qr_runtime(module_loader)
        image = qrcode.make(remote_url)
        output = io.BytesIO()
        image.save(output, format="PNG")
        payload = output.getvalue()
    except Exception:
        raise RuntimeError(
            "SECURE_REVIEW_RUNTIME_REQUIRED: install qrcode==7.4.2 before remote review"
        ) from None
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("SECURE_REVIEW_RUNTIME_REQUIRED: QR renderer did not return PNG")
    return payload


def _load_pairing_ui_runtime(module_loader: Any = None) -> Any:
    loader = module_loader or importlib.import_module
    try:
        return loader("tkinter")
    except Exception:
        raise RuntimeError(
            "SECURE_REVIEW_RUNTIME_REQUIRED: Python tkinter and an interactive desktop "
            "are required for the in-memory pairing window"
        ) from None


class _NativePairingWindow:
    """Display the secret-bearing QR as pixels without a URL or file locator."""

    def __init__(self, qr_png: bytes, fingerprint: str, expires_at: str,
                 tk_module: Any = None) -> None:
        self._tk = tk_module or _load_pairing_ui_runtime()
        self._root: Any = None
        self._image: Any = None
        self._closed = False
        try:
            root = self._tk.Tk()
            self._root = root
            root.withdraw()
            root.title("Hao 安全審片授權")
            root.configure(bg="#090b10")
            root.resizable(False, False)
            root.protocol("WM_DELETE_WINDOW", self.close)
            title = self._tk.Label(
                root, text="掃碼授權這次審片", bg="#090b10", fg="#f7f7fb",
                font=("TkDefaultFont", 18, "bold"), pady=12)
            title.pack()
            note = self._tk.Label(
                root, text="一次性 QR 只存在這個視窗的記憶體中；請在到期前掃描。",
                bg="#090b10", fg="#dce3f4", padx=18, wraplength=430,
                justify="center")
            note.pack()
            encoded = base64.b64encode(qr_png).decode("ascii")
            self._image = self._tk.PhotoImage(data=encoded, format="png")
            del encoded
            image = self._tk.Label(root, image=self._image, bg="#ffffff", padx=10, pady=10)
            image.pack(padx=20, pady=16)
            meta = self._tk.Label(
                root, text="指紋：%s\n配對到期：%s" % (fingerprint, expires_at),
                bg="#090b10", fg="#aeb7cb", padx=18, pady=10, justify="center")
            meta.pack()
            root.update_idletasks()
            root.deiconify()
            root.lift()
            try:
                root.attributes("-topmost", True)
                root.after(1200, self._release_topmost)
            except Exception:
                pass
            root.update_idletasks()
            root.update()
        except Exception:
            self.close()
            raise RuntimeError(
                "SECURE_REVIEW_RUNTIME_REQUIRED: could not open the in-memory native "
                "pairing window on this interactive desktop"
            ) from None

    @property
    def is_open(self) -> bool:
        return not self._closed and self._root is not None

    def _release_topmost(self) -> None:
        if self.is_open:
            try:
                self._root.attributes("-topmost", False)
            except Exception:
                pass

    def pump(self) -> bool:
        if not self.is_open:
            return False
        try:
            self._root.update_idletasks()
            self._root.update()
            return True
        except Exception:
            self.close()
            return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        root, self._root = self._root, None
        self._image = None
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
