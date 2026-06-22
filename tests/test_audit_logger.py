from pathlib import Path
from tempfile import TemporaryDirectory
from corge.logging.audit import AuditLogger


def test_audit_logger():
    with TemporaryDirectory() as d:
        logger = AuditLogger(Path(d))
        logger.record_prompt("Hello World")
        
        log_file = Path(d) / "audit.jsonl"
        assert log_file.exists()
        
        content = log_file.read_text()
        assert "Hello World" in content
        assert "timestamp" in content
