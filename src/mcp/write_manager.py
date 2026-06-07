"""
Write Manager - Phase 4: Write and Enrichment Pipeline
Handles atomic file operations with rollback support.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import os
import shutil
import tempfile
import json
from pathlib import Path
from datetime import datetime


class WriteMode(Enum):
    """File write modes."""
    CREATE = "create"
    UPDATE = "update"
    APPEND = "append"


@dataclass
class WriteOperation:
    """Represents a file write operation."""
    path: str
    content: str
    mode: WriteMode
    title: str = ""
    frontmatter: Optional[dict] = None
    correlation_id: Optional[str] = None


@dataclass
class WriteResult:
    """Result of a write operation."""
    success: bool
    path: str
    operation: WriteMode
    bytes_written: int = 0
    error: Optional[str] = None
    backup_path: Optional[str] = None
    timestamp: str = ""


@dataclass
class TransactionLog:
    """Log of write operations for recovery."""
    transaction_id: str
    operations: list[dict] = field(default_factory=list)
    status: str = "pending"
    started_at: str = ""
    completed_at: Optional[str] = None
    rollback_available: bool = True


class TransactionLogger:
    """Logs transactions for failure recovery."""

    def __init__(self, log_dir: str = ".metadata/transactions"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def create_transaction(self, transaction_id: str) -> TransactionLog:
        """Create a new transaction log."""
        transaction = TransactionLog(
            transaction_id=transaction_id,
            started_at=datetime.utcnow().isoformat()
        )
        self._save_transaction(transaction)
        return transaction

    def add_operation(
        self,
        transaction_id: str,
        operation: WriteOperation,
        result: WriteResult
    ):
        """Add an operation to the transaction."""
        transaction = self._load_transaction(transaction_id)
        if transaction:
            transaction.operations.append({
                "path": operation.path,
                "mode": operation.mode.value,
                "success": result.success,
                "timestamp": result.timestamp,
                "bytes_written": result.bytes_written,
                "error": result.error
            })
            self._save_transaction(transaction)

    def complete_transaction(self, transaction_id: str, success: bool):
        """Mark transaction as completed."""
        transaction = self._load_transaction(transaction_id)
        if transaction:
            transaction.status = "completed" if success else "failed"
            transaction.completed_at = datetime.utcnow().isoformat()
            transaction.rollback_available = not success
            self._save_transaction(transaction)

    def get_pending_transactions(self) -> list[TransactionLog]:
        """Get all pending transactions."""
        transactions = []
        for f in self.log_dir.glob("*.json"):
            transaction = self._load_transaction(f.stem)
            if transaction and transaction.status == "pending":
                transactions.append(transaction)
        return transactions

    def _save_transaction(self, transaction: TransactionLog):
        """Save transaction to disk."""
        path = self.log_dir / f"{transaction.transaction_id}.json"
        with open(path, 'w') as f:
            json.dump({
                "transaction_id": transaction.transaction_id,
                "operations": transaction.operations,
                "status": transaction.status,
                "started_at": transaction.started_at,
                "completed_at": transaction.completed_at,
                "rollback_available": transaction.rollback_available
            }, f, indent=2)

    def _load_transaction(self, transaction_id: str) -> Optional[TransactionLog]:
        """Load transaction from disk."""
        path = self.log_dir / f"{transaction_id}.json"
        if not path.exists():
            return None
        
        with open(path) as f:
            data = json.load(f)
            return TransactionLog(
                transaction_id=data["transaction_id"],
                operations=data["operations"],
                status=data["status"],
                started_at=data["started_at"],
                completed_at=data.get("completed_at"),
                rollback_available=data.get("rollback_available", True)
            )


class RollbackHandler:
    """Handles rollback of failed write operations."""

    def __init__(self, backup_dir: str = ".metadata/backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, path: str) -> Optional[str]:
        """Create backup of existing file."""
        file_path = Path(path)
        if not file_path.exists():
            return None
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        return str(backup_path)

    def rollback_file(self, original_path: str, backup_path: str) -> bool:
        """Restore file from backup."""
        try:
            original = Path(original_path)
            if not original.exists():
                return False
            
            shutil.copy2(backup_path, original)
            return True
        except Exception:
            return False

    def cleanup_old_backups(self, max_age_days: int = 7):
        """Remove backups older than max_age_days."""
        cutoff = datetime.utcnow().timestamp() - (max_age_days * 86400)
        
        for backup_file in self.backup_dir.glob("*"):
            if backup_file.stat().st_mtime < cutoff:
                backup_file.unlink()


class WriteManager:
    """
    Manages atomic file write operations with transaction support.
    """

    def __init__(
        self,
        backup_dir: str = ".metadata/backups",
        transaction_dir: str = ".metadata/transactions"
    ):
        self.transaction_logger = TransactionLogger(transaction_dir)
        self.rollback_handler = RollbackHandler(backup_dir)

    def write(
        self,
        operation: WriteOperation,
        transaction_id: Optional[str] = None
    ) -> WriteResult:
        """
        Perform atomic write operation.
        
        Args:
            operation: WriteOperation to perform
            transaction_id: Optional transaction ID for tracking
            
        Returns:
            WriteResult with operation status
        """
        path = Path(operation.path)
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            
            backup_path = None
            if path.exists() and operation.mode in (WriteMode.UPDATE, WriteMode.APPEND):
                backup_path = self.rollback_handler.create_backup(str(path))
            
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=path.suffix,
                dir=path.parent
            )
            
            try:
                content = self._prepare_content(
                    operation.content,
                    operation.frontmatter,
                    operation.title,
                    operation.correlation_id
                )
                
                with os.fdopen(temp_fd, 'w') as f:
                    f.write(content)
                    bytes_written = f.tell()
                
                shutil.move(temp_path, path)
                
                result = WriteResult(
                    success=True,
                    path=str(path),
                    operation=operation.mode,
                    bytes_written=bytes_written,
                    backup_path=backup_path,
                    timestamp=datetime.utcnow().isoformat()
                )
                
                if transaction_id:
                    self.transaction_logger.add_operation(
                        transaction_id, operation, result
                    )
                
                return result
                
            except Exception as e:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise RuntimeError(f"Write failed: {e}")
                
        except Exception as e:
            return WriteResult(
                success=False,
                path=str(path),
                operation=operation.mode,
                error=str(e),
                timestamp=datetime.utcnow().isoformat()
            )

    def write_batch(
        self,
        operations: list[WriteOperation]
    ) -> list[WriteResult]:
        """Execute multiple write operations as a batch."""
        import uuid
        transaction_id = str(uuid.uuid4())
        
        self.transaction_logger.create_transaction(transaction_id)
        
        results = []
        for op in operations:
            result = self.write(op, transaction_id)
            results.append(result)
            
            if not result.success:
                self._rollback_batch(results)
                self.transaction_logger.complete_transaction(
                    transaction_id, False
                )
                return results
        
        self.transaction_logger.complete_transaction(transaction_id, True)
        return results

    def _prepare_content(
        self,
        content: str,
        frontmatter: Optional[dict],
        title: str,
        correlation_id: Optional[str]
    ) -> str:
        """Prepare content with optional frontmatter."""
        if not frontmatter and not title:
            return content
        
        fm = frontmatter or {}
        if title and "title" not in fm:
            fm["title"] = title
        if correlation_id and "provenance" not in fm:
            fm["provenance"] = correlation_id
        if "last_modified" not in fm:
            fm["last_modified"] = datetime.utcnow().isoformat()
        
        fm_yaml = self._dict_to_yaml(fm)
        
        return f"---\n{fm_yaml}---\n\n{content}"

    def _dict_to_yaml(self, d: dict) -> str:
        """Simple dict to YAML conversion."""
        lines = []
        for key, value in d.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
        return '\n'.join(lines)

    def _rollback_batch(self, results: list[WriteResult]):
        """Rollback a batch of operations."""
        for result in reversed(results):
            if result.success and result.backup_path:
                self.rollback_handler.rollback_file(
                    result.path, result.backup_path
                )

    def verify_write(self, path: str, expected_content: str) -> bool:
        """Verify that file was written correctly."""
        try:
            with open(path) as f:
                actual = f.read()
            return expected_content in actual
        except Exception:
            return False

    def get_file_info(self, path: str) -> Optional[dict]:
        """Get metadata about a written file."""
        try:
            stat = os.stat(path)
            return {
                "path": path,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception:
            return None
