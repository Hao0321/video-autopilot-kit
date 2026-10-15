"""Delivered-scope control: hidden folders are payload, not audit exclusions."""
from pathlib import Path
import tempfile
from check_release_exposure import audit


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-delivered-scope-") as raw:
        root = Path(raw)
        (root / ".rd").mkdir()
        path = root / ".rd" / "private.bin"
        path.write_bytes(("C:" + "/Users/" + "fixture-owner/private").encode())
        report = audit(root)
        assert report["summary"]["enumerated"] == 1, "hidden delivered payload was omitted"
        assert report["status"] == "REVIEW", "hidden private path became a false clean report"
        assert report["findings"][0]["path"] == ".rd/private.bin"


if __name__ == "__main__":
    run_self_test()
    print("Delivered hidden-folder coverage control passed")
