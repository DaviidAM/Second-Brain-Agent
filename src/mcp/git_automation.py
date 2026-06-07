"""
Git Automation - Phase 6: Git Automation and Auditability
Handles auto-commit for created/updated markdown files.
"""

import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class CommitType(Enum):
    """Types of commits."""

    ADD = "add"
    UPDATE = "update"
    MERGE = "merge"
    ENRICH = "enrich"


@dataclass
class CommitMessage:
    """Structured commit message."""

    type: CommitType
    title: str
    body: str = ""
    trailers: dict = field(default_factory=dict)

    def format(self) -> str:
        """Format commit message."""
        prefixes = {
            CommitType.ADD: "[enrich] Add:",
            CommitType.UPDATE: "[enrich] Update:",
            CommitType.MERGE: "[merge] Merge:",
            CommitType.ENRICH: "[enrich] Enrich:",
        }

        msg = f"{prefixes[self.type]} {self.title}"

        if self.body:
            msg += f"\n\n{self.body}"

        for key, value in self.trailers.items():
            msg += f"\n{key}: {value}"

        return msg


@dataclass
class CommitResult:
    """Result of a commit operation."""

    success: bool
    commit_hash: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    files_changed: list[str] = field(default_factory=list)


class CommitMessageGenerator:
    """Generates standardized commit messages."""

    def __init__(self):
        self._templates = {
            CommitType.ADD: self._add_template,
            CommitType.UPDATE: self._update_template,
            CommitType.MERGE: self._merge_template,
            CommitType.ENRICH: self._enrich_template,
        }

    def generate(
        self,
        commit_type: CommitType,
        title: str,
        correlation_id: Optional[str] = None,
        enrichment_rationale: Optional[str] = None,
    ) -> CommitMessage:
        """Generate commit message."""
        template_fn = self._templates.get(commit_type, self._default_template)

        return template_fn(title, correlation_id, enrichment_rationale)

    def _add_template(
        self, title: str, correlation_id: Optional[str], rationale: Optional[str]
    ) -> CommitMessage:
        return CommitMessage(
            type=CommitType.ADD,
            title=title,
            body=rationale or f"Added new document: {title}",
            trailers=self._build_trailers(correlation_id, rationale),
        )

    def _update_template(
        self, title: str, correlation_id: Optional[str], rationale: Optional[str]
    ) -> CommitMessage:
        return CommitMessage(
            type=CommitType.UPDATE,
            title=title,
            body=rationale or f"Updated document: {title}",
            trailers=self._build_trailers(correlation_id, rationale),
        )

    def _merge_template(
        self, title: str, correlation_id: Optional[str], rationale: Optional[str]
    ) -> CommitMessage:
        return CommitMessage(
            type=CommitType.MERGE,
            title=title,
            body=rationale or f"Merged content into: {title}",
            trailers=self._build_trailers(correlation_id, rationale),
        )

    def _enrich_template(
        self, title: str, correlation_id: Optional[str], rationale: Optional[str]
    ) -> CommitMessage:
        return CommitMessage(
            type=CommitType.ENRICH,
            title=title,
            body=rationale or f"Enriched knowledge base with: {title}",
            trailers=self._build_trailers(correlation_id, rationale),
        )

    def _default_template(
        self, title: str, correlation_id: Optional[str], rationale: Optional[str]
    ) -> CommitMessage:
        return CommitMessage(
            type=CommitType.ENRICH,
            title=title,
            body=rationale or f"Updated: {title}",
            trailers=self._build_trailers(correlation_id, rationale),
        )

    def _build_trailers(
        self, correlation_id: Optional[str], rationale: Optional[str]
    ) -> dict:
        trailers = {}

        if correlation_id:
            trailers["provenance"] = correlation_id

        if rationale:
            trailers["enrichment_rationale"] = rationale

        return trailers


class CommitPolicy:
    """Defines commit policies and rules."""

    def __init__(
        self,
        auto_commit_enabled: bool = True,
        require_message: bool = True,
        max_file_size: int = 10 * 1024 * 1024,
        allowed_extensions: Optional[list[str]] = None,
    ):
        self.auto_commit_enabled = auto_commit_enabled
        self.require_message = require_message
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or [".md", ".yaml", ".json"]

    def can_commit(self, file_path: str) -> tuple[bool, str]:
        """Check if file can be committed."""
        path = Path(file_path)

        if not path.exists():
            return False, "File does not exist"

        if path.stat().st_size > self.max_file_size:
            return False, f"File too large: {path.stat().st_size} bytes"

        if path.suffix not in self.allowed_extensions:
            return False, f"File type not allowed: {path.suffix}"

        return True, "OK"

    def should_commit(self, file_path: str, operation: CommitType) -> bool:
        """Determine if commit should be performed."""
        if not self.auto_commit_enabled:
            return False

        can_commit, _ = self.can_commit(file_path)
        return can_commit


class GitAutoCommit:
    """
    Main git automation class for auto-committing knowledge base changes.
    """

    def __init__(
        self,
        repo_path: str = ".",
        author_name: str = "MCP Knowledge Assistant",
        author_email: str = "mcp@knowledge.local",
        policy: Optional[CommitPolicy] = None,
    ):
        self.repo_path = Path(repo_path)
        self.author_name = author_name
        self.author_email = author_email
        self.policy = policy or CommitPolicy()
        self.message_generator = CommitMessageGenerator()

    def commit_file(
        self,
        file_path: str,
        commit_type: CommitType,
        correlation_id: Optional[str] = None,
        enrichment_rationale: Optional[str] = None,
    ) -> CommitResult:
        """
        Commit a single file.

        Args:
            file_path: Path to file to commit
            commit_type: Type of commit
            correlation_id: Optional correlation ID for tracking
            enrichment_rationale: Optional rationale for enrichment

        Returns:
            CommitResult with operation status
        """
        can_commit, reason = self.policy.can_commit(file_path)
        if not can_commit:
            return CommitResult(success=False, error=reason)

        path = Path(file_path)
        title = path.stem

        message = self.message_generator.generate(
            commit_type, title, correlation_id, enrichment_rationale
        )

        try:
            self._git_add(file_path)

            result = self._git_commit(message.format())

            if result.returncode == 0:
                commit_hash = self._get_last_commit_hash()
                return CommitResult(
                    success=True,
                    commit_hash=commit_hash,
                    message=message.format(),
                    files_changed=[file_path],
                )
            else:
                return CommitResult(
                    success=False,
                    error=result.stderr or "Commit failed",
                    message=message.format(),
                )

        except Exception as e:
            return CommitResult(success=False, error=str(e))

    def commit_files(
        self,
        files: list[str],
        commit_type: CommitType,
        correlation_id: Optional[str] = None,
        enrichment_rationale: Optional[str] = None,
    ) -> CommitResult:
        """Commit multiple files in one operation."""
        valid_files = []
        for f in files:
            can_commit, _ = self.policy.can_commit(f)
            if can_commit:
                valid_files.append(f)

        if not valid_files:
            return CommitResult(success=False, error="No valid files to commit")

        title = f"{len(valid_files)} file(s)"

        message = self.message_generator.generate(
            commit_type, title, correlation_id, enrichment_rationale
        )

        try:
            for f in valid_files:
                self._git_add(f)

            result = self._git_commit(message.format())

            if result.returncode == 0:
                commit_hash = self._get_last_commit_hash()
                return CommitResult(
                    success=True,
                    commit_hash=commit_hash,
                    message=message.format(),
                    files_changed=valid_files,
                )
            else:
                return CommitResult(
                    success=False,
                    error=result.stderr or "Commit failed",
                    message=message.format(),
                )

        except Exception as e:
            return CommitResult(success=False, error=str(e))

    def get_status(self) -> list[dict]:
        """Get git status of repository."""
        try:
            result = self._git_status()
            if result.returncode != 0:
                return []

            lines = result.stdout.strip().split("\n")
            status = []

            for line in lines:
                if line.startswith(("M ", "A ", "?? ")):
                    status.append({"path": line[3:], "status": line[:2].strip()})

            return status

        except Exception:
            return []

    def get_last_commit(self) -> Optional[dict]:
        """Get information about last commit."""
        try:
            result = self._git_log(1)
            if result.returncode != 0:
                return None

            lines = result.stdout.strip().split("\n")
            commit = {}

            for line in lines:
                if line.startswith("commit "):
                    commit["hash"] = line[7:]
                elif line.startswith("Author:"):
                    commit["author"] = line[7:]
                elif line.startswith("Date:"):
                    commit["date"] = line[7:]
                elif line and not line.startswith("    "):
                    commit["message"] = line

            return commit

        except Exception:
            return None

    def _git_add(self, file_path: str):
        """Stage file for commit."""
        subprocess.run(
            ["git", "add", file_path],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )

    def _git_commit(self, message: str) -> subprocess.CompletedProcess:
        """Create commit."""
        return subprocess.run(
            ["git", "commit", "-m", message], cwd=self.repo_path, capture_output=True
        )

    def _git_status(self) -> subprocess.CompletedProcess:
        """Get git status."""
        return subprocess.run(
            ["git", "status", "--porcelain"], cwd=self.repo_path, capture_output=True
        )

    def _git_log(self, n: int) -> subprocess.CompletedProcess:
        """Get git log."""
        return subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:%H%n%an%n%ae%n%ad%n%s"],
            cwd=self.repo_path,
            capture_output=True,
        )

    def _get_last_commit_hash(self) -> Optional[str]:
        """Get hash of last commit."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
                text=True,
            )
            return result.stdout.strip()
        except Exception:
            return None

    def is_git_repo(self) -> bool:
        """Check if directory is a git repository."""
        git_dir = self.repo_path / ".git"
        return git_dir.exists()
