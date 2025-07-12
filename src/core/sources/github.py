"""GitHub repository content source implementation."""

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from ..config.settings import get_logger
from ..config.sources import ContentSource, SourceType

logger = get_logger(__name__)


class GitHubSourceManager:
    """Manages GitHub repository content sources."""

    def __init__(self, cache_dir: Path):
        """Initialize GitHub source manager."""
        self.cache_dir = cache_dir
        self.repos_dir = cache_dir / "repositories"
        self.repos_dir.mkdir(parents=True, exist_ok=True)

    def get_repo_path(self, source: ContentSource) -> Path:
        """Get local path for a repository."""
        if source.type != SourceType.GITHUB:
            raise ValueError(f"Source {source.name} is not a GitHub source")
        return self.repos_dir / source.name

    async def ensure_repository(self, source: ContentSource) -> Path:
        """Ensure repository is cloned and up to date."""
        if source.type != SourceType.GITHUB:
            raise ValueError(f"Source {source.name} is not a GitHub source")

        repo_path = self.get_repo_path(source)

        if repo_path.exists():
            if source.auto_update:
                await self._update_repository(source, repo_path)
        else:
            await self._clone_repository(source, repo_path)

        return repo_path

    async def _clone_repository(self, source: ContentSource, repo_path: Path) -> None:
        """Clone a repository."""
        logger.info(f"Cloning repository {source.url} to {repo_path}")

        try:
            # Prepare git clone command
            cmd = ["git", "clone", "--depth", "1"]
            if source.branch and source.branch != "master":
                cmd.extend(["--branch", source.branch])
            cmd.extend([source.url, str(repo_path)])

            # Run git clone
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown git error"
                raise RuntimeError(f"Failed to clone repository: {error_msg}")

            logger.info(f"Successfully cloned {source.name}")

        except Exception as e:
            # Clean up partial clone
            if repo_path.exists():
                shutil.rmtree(repo_path)
            raise RuntimeError(f"Failed to clone repository {source.name}: {e}")

    async def _update_repository(self, source: ContentSource, repo_path: Path) -> None:
        """Update an existing repository."""
        logger.info(f"Updating repository {source.name}")

        try:
            # Check if it's a git repository
            if not (repo_path / ".git").exists():
                logger.warning(
                    f"Directory {repo_path} is not a git repository, re-cloning"
                )
                shutil.rmtree(repo_path)
                await self._clone_repository(source, repo_path)
                return

            # Run git pull
            process = await asyncio.create_subprocess_exec(
                "git",
                "pull",
                "--depth",
                "1",
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown git error"
                logger.warning(
                    f"Failed to update repository {source.name}: {error_msg}"
                )
                # Don't raise error - use existing content
            else:
                logger.info(f"Successfully updated {source.name}")

        except Exception as e:
            logger.warning(f"Failed to update repository {source.name}: {e}")
            # Don't raise error - use existing content

    def is_git_available(self) -> bool:
        """Check if git is available on the system."""
        try:
            subprocess.run(
                ["git", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_repository_info(self, source: ContentSource) -> Optional[dict]:
        """Get information about a cloned repository."""
        repo_path = self.get_repo_path(source)

        if not repo_path.exists() or not (repo_path / ".git").exists():
            return None

        try:
            # Get current commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            commit_hash = result.stdout.strip()

            # Get last commit date
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            last_commit_date = result.stdout.strip()

            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = result.stdout.strip()

            return {
                "commit_hash": commit_hash,
                "last_commit_date": last_commit_date,
                "current_branch": current_branch,
                "local_path": str(repo_path),
            }

        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get repository info for {source.name}: {e}")
            return None

    def remove_repository(self, source: ContentSource) -> bool:
        """Remove a cloned repository."""
        repo_path = self.get_repo_path(source)

        if repo_path.exists():
            try:
                shutil.rmtree(repo_path)
                logger.info(f"Removed repository {source.name}")
                return True
            except Exception as e:
                logger.error(f"Failed to remove repository {source.name}: {e}")
                return False

        return True  # Already removed

    def list_content_files(self, source: ContentSource) -> list[Path]:
        """List all JSON content files in a repository."""
        repo_path = self.get_repo_path(source)

        if not repo_path.exists():
            return []

        # Find all JSON files, excluding common non-content files
        json_files = []
        exclude_patterns = {
            "package.json",
            "tsconfig.json",
            ".json",
            "meta.json",
            "node_modules",
            ".git",
            "__pycache__",
        }

        for json_file in repo_path.rglob("*.json"):
            # Skip if matches exclude patterns
            if any(pattern in str(json_file) for pattern in exclude_patterns):
                continue

            # Skip if file is too small (likely not content)
            try:
                if json_file.stat().st_size < 50:  # Less than 50 bytes
                    continue
            except OSError:
                continue

            json_files.append(json_file)

        return sorted(json_files)
