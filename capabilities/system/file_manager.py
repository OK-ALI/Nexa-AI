"""
File Manager - File Operations & Organization System
Phase 21: Provides safe file management operations including create, move, copy,
delete (via Recycle Bin), rename, search, organization, and compression.
"""

import logging
import os
import shutil
import hashlib
import zipfile
import time
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Protected system directories that should never be modified
PROTECTED_DIRS = {
    Path(os.environ.get('SystemRoot', 'C:\\Windows')).resolve(),
    Path(os.environ.get('ProgramFiles', 'C:\\Program Files')).resolve(),
    Path(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')).resolve(),
    Path(os.environ.get('SystemRoot', 'C:\\Windows')).resolve() / 'System32',
    Path(os.environ.get('ProgramData', 'C:\\ProgramData')).resolve(),
}

# Common user directories
USER_HOME = Path.home()
USER_DIRS = {
    'desktop': USER_HOME / 'Desktop',
    'documents': USER_HOME / 'Documents',
    'downloads': USER_HOME / 'Downloads',
    'pictures': USER_HOME / 'Pictures',
    'videos': USER_HOME / 'Videos',
    'music': USER_HOME / 'Music',
}

# File categories for organization
FILE_CATEGORIES = {
    'images': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.heic'},
    'documents': {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv'},
    'videos': {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'},
    'audio': {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'},
    'archives': {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'},
    'code': {'.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.json', '.xml', '.yaml', '.yml'},
    'executables': {'.exe', '.msi', '.bat', '.cmd', '.ps1', '.sh'},
}

# Size thresholds
LARGE_FILE_WARNING_MB = 100  # Warn for files > 100MB
MAX_SEARCH_RESULTS = 50


class FileManager:
    """
    Manages file operations with safety checks and organization features.
    All destructive operations use Recycle Bin via send2trash.
    """
    
    def __init__(self):
        """Initialize File Manager."""
        self._send2trash_available = False
        try:
            import send2trash as _s2t
            self._send2trash = _s2t
            self._send2trash_available = True
        except ImportError:
            self._send2trash = None
            logger.warning("send2trash not installed - delete operations will be disabled for safety")
        
        logger.info("File Manager initialized")
    
    # ========================================
    # SAFETY CHECKS
    # ========================================
    
    def _is_protected_path(self, path: Path) -> bool:
        """Check if path is in a protected system directory."""
        try:
            resolved = path.resolve()
            for protected in PROTECTED_DIRS:
                try:
                    resolved.relative_to(protected)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return True  # Default to protected if we can't resolve
    
    def _validate_path(self, path_str: str) -> Tuple[bool, Path, str]:
        """
        Validate and resolve a file path.
        
        Returns:
            Tuple of (is_valid, resolved_path, error_message)
        """
        if not path_str or not path_str.strip():
            return False, Path(), "No path provided"
        
        path = Path(path_str.strip())
        
        # Resolve user directory shortcuts
        lower = path_str.strip().lower()
        for name, user_dir in USER_DIRS.items():
            if lower.startswith(name):
                remaining = path_str.strip()[len(name):].lstrip('/\\')
                path = user_dir / remaining if remaining else user_dir
                break
        
        # Make absolute if relative
        if not path.is_absolute():
            # Default to user's home directory for relative paths
            path = USER_HOME / path
        
        try:
            resolved = path.resolve()
        except Exception as e:
            return False, path, f"Invalid path: {e}"
        
        if self._is_protected_path(resolved):
            return False, resolved, f"Cannot modify protected system path: {resolved}"
        
        return True, resolved, ""
    
    def _get_file_size_str(self, size_bytes: int) -> str:
        """Convert bytes to human-readable size string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def _resolve_user_path(self, path_str: str) -> Path:
        """Resolve common user directory names to actual paths."""
        lower = path_str.strip().lower()
        
        # Direct directory name match
        for name, user_dir in USER_DIRS.items():
            if lower == name or lower == name + 's':
                return user_dir
        
        # Path starting with directory name
        for name, user_dir in USER_DIRS.items():
            if lower.startswith(name + '\\') or lower.startswith(name + '/'):
                remaining = path_str.strip()[len(name) + 1:]
                return user_dir / remaining
        
        path = Path(path_str.strip())
        if not path.is_absolute():
            return USER_HOME / path
        return path
    
    # ========================================
    # CORE FILE OPERATIONS
    # ========================================
    
    def create_file(self, file_path: str, content: str = "") -> str:
        """
        Create a new file with optional content.
        
        Args:
            file_path: Path where the file should be created
            content: Optional text content for the file
            
        Returns:
            str: Result message
        """
        try:
            valid, path, error = self._validate_path(file_path)
            if not valid:
                return f"Cannot create file: {error}"
            
            if path.exists():
                return f"File already exists: {path.name}. Use rename_file to change its name."
            
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            path.write_text(content, encoding='utf-8')
            
            size = self._get_file_size_str(path.stat().st_size)
            logger.info(f"Created file: {path} ({size})")
            return f"Created file '{path.name}' at {path.parent} ({size})"
            
        except PermissionError:
            return f"Permission denied creating file at {file_path}"
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return f"Error creating file: {str(e)}"
    
    def move_file(self, source: str, destination: str) -> str:
        """
        Move a file or folder to a new location.
        
        Args:
            source: Source file/folder path
            destination: Destination path or directory
            
        Returns:
            str: Result message
        """
        try:
            valid_src, src_path, error = self._validate_path(source)
            if not valid_src:
                return f"Invalid source: {error}"
            
            if not src_path.exists():
                return f"Source not found: {source}"
            
            valid_dst, dst_path, error = self._validate_path(destination)
            if not valid_dst:
                return f"Invalid destination: {error}"
            
            # If destination is a directory, move into it
            if dst_path.is_dir():
                dst_path = dst_path / src_path.name
            
            if dst_path.exists():
                return f"Destination already exists: {dst_path.name}. Delete it first or choose a different name."
            
            # Create parent dirs if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check file size for warning
            if src_path.is_file():
                size_mb = src_path.stat().st_size / (1024 * 1024)
                if size_mb > LARGE_FILE_WARNING_MB:
                    logger.warning(f"Moving large file: {self._get_file_size_str(src_path.stat().st_size)}")
            
            shutil.move(str(src_path), str(dst_path))
            
            item_type = "folder" if dst_path.is_dir() else "file"
            logger.info(f"Moved {item_type}: {src_path} -> {dst_path}")
            return f"Moved {item_type} '{src_path.name}' to {dst_path.parent}"
            
        except PermissionError:
            return f"Permission denied moving '{source}'"
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return f"Error moving file: {str(e)}"
    
    def copy_file(self, source: str, destination: str) -> str:
        """
        Copy a file or folder to a new location.
        
        Args:
            source: Source file/folder path
            destination: Destination path or directory
            
        Returns:
            str: Result message
        """
        try:
            valid_src, src_path, error = self._validate_path(source)
            if not valid_src:
                return f"Invalid source: {error}"
            
            if not src_path.exists():
                return f"Source not found: {source}"
            
            valid_dst, dst_path, error = self._validate_path(destination)
            if not valid_dst:
                return f"Invalid destination: {error}"
            
            # If destination is a directory, copy into it
            if dst_path.is_dir():
                dst_path = dst_path / src_path.name
            
            # Handle name conflicts
            if dst_path.exists():
                stem = dst_path.stem
                suffix = dst_path.suffix
                counter = 1
                while dst_path.exists():
                    dst_path = dst_path.parent / f"{stem} ({counter}){suffix}"
                    counter += 1
            
            # Create parent dirs if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            if src_path.is_dir():
                shutil.copytree(str(src_path), str(dst_path))
                item_type = "folder"
            else:
                shutil.copy2(str(src_path), str(dst_path))
                item_type = "file"
                size = self._get_file_size_str(dst_path.stat().st_size)
                logger.info(f"Copied {item_type}: {src_path} -> {dst_path} ({size})")
                return f"Copied {item_type} '{src_path.name}' to {dst_path.parent} ({size})"
            
            logger.info(f"Copied {item_type}: {src_path} -> {dst_path}")
            return f"Copied {item_type} '{src_path.name}' to {dst_path.parent}"
            
        except PermissionError:
            return f"Permission denied copying '{source}'"
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return f"Error copying file: {str(e)}"
    
    def delete_file(self, file_path: str) -> str:
        """
        Delete a file or folder by moving it to the Recycle Bin.
        Uses send2trash for safe, recoverable deletion.
        
        Args:
            file_path: Path of file/folder to delete
            
        Returns:
            str: Result message
        """
        try:
            if not self._send2trash_available:
                return "Delete is disabled for safety. Install send2trash: pip install send2trash"
            
            valid, path, error = self._validate_path(file_path)
            if not valid:
                return f"Cannot delete: {error}"
            
            if not path.exists():
                return f"File not found: {file_path}"
            
            item_type = "folder" if path.is_dir() else "file"
            name = path.name
            
            if path.is_file():
                size = self._get_file_size_str(path.stat().st_size)
            else:
                # Calculate folder size
                total = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                size = self._get_file_size_str(total)
            
            # Send to Recycle Bin (recoverable)
            self._send2trash.send2trash(str(path))
            
            logger.info(f"Deleted {item_type} to Recycle Bin: {path} ({size})")
            return f"Moved {item_type} '{name}' to Recycle Bin ({size}). You can restore it from the Recycle Bin if needed."
            
        except PermissionError:
            return f"Permission denied deleting '{file_path}'"
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return f"Error deleting file: {str(e)}"
    
    def rename_file(self, file_path: str, new_name: str) -> str:
        """
        Rename a file or folder.
        
        Args:
            file_path: Current path of the file/folder
            new_name: New name (just the filename, not full path)
            
        Returns:
            str: Result message
        """
        try:
            valid, path, error = self._validate_path(file_path)
            if not valid:
                return f"Cannot rename: {error}"
            
            if not path.exists():
                return f"File not found: {file_path}"
            
            # Clean the new name
            new_name = new_name.strip()
            if not new_name:
                return "No new name provided"
            
            # Check for invalid characters
            invalid_chars = '<>:"/\\|?*'
            if any(c in new_name for c in invalid_chars):
                return f"Invalid characters in filename. Avoid: {invalid_chars}"
            
            new_path = path.parent / new_name
            
            if new_path.exists():
                return f"A file named '{new_name}' already exists in that location"
            
            old_name = path.name
            path.rename(new_path)
            
            item_type = "folder" if new_path.is_dir() else "file"
            logger.info(f"Renamed {item_type}: {old_name} -> {new_name}")
            return f"Renamed '{old_name}' to '{new_name}'"
            
        except PermissionError:
            return f"Permission denied renaming '{file_path}'"
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            return f"Error renaming file: {str(e)}"
    
    # ========================================
    # SEARCH & DISCOVERY
    # ========================================
    
    def search_files(self, query: str, location: str = "", file_type: str = "") -> str:
        """
        Search for files by name pattern.
        
        Args:
            query: Search term (supports wildcards: *.txt, report*)
            location: Directory to search in (default: user home)
            file_type: Optional file extension filter (e.g., 'pdf', 'txt')
            
        Returns:
            str: Search results
        """
        try:
            # Determine search root
            if location:
                search_root = self._resolve_user_path(location)
            else:
                search_root = USER_HOME
            
            if not search_root.exists():
                return f"Search location not found: {location}"
            
            # Build search pattern
            search_term = query.strip().lower()
            
            # Add extension filter if specified
            ext_filter = None
            if file_type:
                ext_filter = file_type.strip().lower()
                if not ext_filter.startswith('.'):
                    ext_filter = '.' + ext_filter
            
            results = []
            searched = 0
            max_search = 50000  # Limit to prevent hanging on huge directories
            
            try:
                for item in search_root.rglob('*'):
                    searched += 1
                    if searched > max_search:
                        break
                    
                    if not item.is_file():
                        continue
                    
                    # Skip hidden/system files
                    if any(part.startswith('.') for part in item.parts):
                        continue
                    
                    name_lower = item.name.lower()
                    
                    # Check name match
                    if search_term not in name_lower:
                        continue
                    
                    # Check extension filter
                    if ext_filter and item.suffix.lower() != ext_filter:
                        continue
                    
                    size = self._get_file_size_str(item.stat().st_size)
                    modified = datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d')
                    
                    results.append({
                        'name': item.name,
                        'path': str(item),
                        'size': size,
                        'modified': modified,
                    })
                    
                    if len(results) >= MAX_SEARCH_RESULTS:
                        break
                        
            except PermissionError:
                pass  # Skip inaccessible directories
            
            if not results:
                type_msg = f" (.{file_type})" if file_type else ""
                return f"No files matching '{query}'{type_msg} found in {search_root.name}"
            
            # Format results
            lines = [f"Found {len(results)} file{'s' if len(results) > 1 else ''} matching '{query}':"]
            for r in results[:20]:  # Show first 20
                lines.append(f"  • {r['name']} ({r['size']}, {r['modified']}) - {r['path']}")
            
            if len(results) > 20:
                lines.append(f"  ... and {len(results) - 20} more")
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return f"Error searching files: {str(e)}"
    
    def get_recent_files(self, location: str = "downloads", count: int = 10) -> str:
        """
        Get recently modified files in a directory.
        
        Args:
            location: Directory to check (default: Downloads)
            count: Number of recent files to show
            
        Returns:
            str: List of recent files
        """
        try:
            search_dir = self._resolve_user_path(location)
            
            if not search_dir.exists():
                return f"Directory not found: {location}"
            
            # Get all files with their modification times
            files = []
            try:
                for item in search_dir.iterdir():
                    if item.is_file() and not item.name.startswith('.'):
                        try:
                            stat = item.stat()
                            files.append({
                                'name': item.name,
                                'path': str(item),
                                'size': self._get_file_size_str(stat.st_size),
                                'modified': datetime.fromtimestamp(stat.st_mtime),
                            })
                        except (PermissionError, OSError):
                            continue
            except PermissionError:
                return f"Permission denied accessing {location}"
            
            if not files:
                return f"No files found in {search_dir.name}"
            
            # Sort by modification time (newest first)
            files.sort(key=lambda f: f['modified'], reverse=True)
            files = files[:count]
            
            lines = [f"Recent files in {search_dir.name}:"]
            for f in files:
                age = datetime.now() - f['modified']
                if age.days == 0:
                    if age.seconds < 3600:
                        time_ago = f"{age.seconds // 60} minutes ago"
                    else:
                        time_ago = f"{age.seconds // 3600} hours ago"
                elif age.days == 1:
                    time_ago = "yesterday"
                elif age.days < 7:
                    time_ago = f"{age.days} days ago"
                else:
                    time_ago = f['modified'].strftime('%Y-%m-%d')
                
                lines.append(f"  • {f['name']} ({f['size']}, {time_ago})")
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"Error getting recent files: {e}")
            return f"Error getting recent files: {str(e)}"
    
    def find_duplicates(self, location: str = "downloads") -> str:
        """
        Find duplicate files in a directory (by size + partial hash).
        
        Args:
            location: Directory to check for duplicates
            
        Returns:
            str: Duplicate file report
        """
        try:
            search_dir = self._resolve_user_path(location)
            
            if not search_dir.exists():
                return f"Directory not found: {location}"
            
            # Group files by size first (quick filter)
            size_groups: Dict[int, List[Path]] = {}
            file_count = 0
            
            try:
                for item in search_dir.rglob('*'):
                    if not item.is_file() or item.name.startswith('.'):
                        continue
                    file_count += 1
                    if file_count > 10000:  # Limit scan
                        break
                    try:
                        size = item.stat().st_size
                        if size > 0:  # Skip empty files
                            if size not in size_groups:
                                size_groups[size] = []
                            size_groups[size].append(item)
                    except (PermissionError, OSError):
                        continue
            except PermissionError:
                return f"Permission denied accessing {location}"
            
            # Check actual duplicates using hash for same-size files
            duplicates = []
            
            for size, files in size_groups.items():
                if len(files) < 2:
                    continue
                
                # Hash first 8KB of each file for quick comparison
                hash_groups: Dict[str, List[Path]] = {}
                for f in files:
                    try:
                        hasher = hashlib.md5()
                        with open(f, 'rb') as fh:
                            chunk = fh.read(8192)
                            hasher.update(chunk)
                        h = hasher.hexdigest()
                        if h not in hash_groups:
                            hash_groups[h] = []
                        hash_groups[h].append(f)
                    except (PermissionError, OSError):
                        continue
                
                for h, group in hash_groups.items():
                    if len(group) >= 2:
                        duplicates.append({
                            'size': self._get_file_size_str(size),
                            'files': [str(f) for f in group],
                        })
            
            if not duplicates:
                return f"No duplicate files found in {search_dir.name} ({file_count} files scanned)"
            
            total_dupes = sum(len(d['files']) - 1 for d in duplicates)
            lines = [f"Found {total_dupes} duplicate files in {search_dir.name}:"]
            
            for i, dup in enumerate(duplicates[:15]):  # Show first 15 groups
                lines.append(f"\n  Group {i + 1} ({dup['size']}):")
                for f in dup['files']:
                    lines.append(f"    - {Path(f).name}")
            
            if len(duplicates) > 15:
                lines.append(f"\n  ... and {len(duplicates) - 15} more duplicate groups")
            
            lines.append(f"\nUse delete_file to remove unwanted duplicates (they go to Recycle Bin).")
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"Error finding duplicates: {e}")
            return f"Error finding duplicates: {str(e)}"
    
    # ========================================
    # ORGANIZATION
    # ========================================
    
    def organize_files(self, location: str = "downloads") -> str:
        """
        Organize files into category subfolders (Images, Documents, Videos, etc.).
        
        Args:
            location: Directory to organize (default: Downloads)
            
        Returns:
            str: Organization report
        """
        try:
            target_dir = self._resolve_user_path(location)
            
            if not target_dir.exists():
                return f"Directory not found: {location}"
            
            valid, resolved, error = self._validate_path(str(target_dir))
            if not valid:
                return f"Cannot organize: {error}"
            
            moved_counts: Dict[str, int] = {}
            errors = 0
            skipped = 0
            
            # Process only files in the top level (not subdirs)
            for item in target_dir.iterdir():
                if not item.is_file() or item.name.startswith('.'):
                    continue
                
                ext = item.suffix.lower()
                category = None
                
                for cat_name, extensions in FILE_CATEGORIES.items():
                    if ext in extensions:
                        category = cat_name.capitalize()
                        break
                
                if not category:
                    skipped += 1
                    continue
                
                # Create category subfolder
                cat_dir = target_dir / category
                cat_dir.mkdir(exist_ok=True)
                
                # Move file
                dest = cat_dir / item.name
                if dest.exists():
                    # Add number suffix for conflicts
                    stem = item.stem
                    counter = 1
                    while dest.exists():
                        dest = cat_dir / f"{stem} ({counter}){item.suffix}"
                        counter += 1
                
                try:
                    shutil.move(str(item), str(dest))
                    moved_counts[category] = moved_counts.get(category, 0) + 1
                except Exception:
                    errors += 1
            
            if not moved_counts:
                return f"No files to organize in {target_dir.name}. Files are either already organized or have unrecognized types."
            
            total = sum(moved_counts.values())
            lines = [f"Organized {total} files in {target_dir.name}:"]
            for cat, count in sorted(moved_counts.items()):
                lines.append(f"  • {cat}: {count} file{'s' if count > 1 else ''}")
            
            if skipped:
                lines.append(f"  • Skipped: {skipped} file{'s' if skipped > 1 else ''} (unrecognized type)")
            if errors:
                lines.append(f"  ⚠ {errors} file{'s' if errors > 1 else ''} could not be moved")
            
            logger.info(f"Organized {total} files in {target_dir}")
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"Error organizing files: {e}")
            return f"Error organizing files: {str(e)}"
    
    def cleanup_downloads(self) -> str:
        """
        Clean up the Downloads folder: organize files, report old/large files.
        
        Returns:
            str: Cleanup report
        """
        try:
            downloads = USER_DIRS.get('downloads', USER_HOME / 'Downloads')
            
            if not downloads.exists():
                return "Downloads folder not found"
            
            # Analyze the folder
            total_files = 0
            total_size = 0
            old_files = []  # Files older than 30 days
            large_files = []  # Files > 100MB
            
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            for item in downloads.iterdir():
                if not item.is_file() or item.name.startswith('.'):
                    continue
                
                total_files += 1
                try:
                    stat = item.stat()
                    total_size += stat.st_size
                    
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    if modified < thirty_days_ago:
                        old_files.append({
                            'name': item.name,
                            'size': stat.st_size,
                            'modified': modified,
                        })
                    
                    if stat.st_size > LARGE_FILE_WARNING_MB * 1024 * 1024:
                        large_files.append({
                            'name': item.name,
                            'size': stat.st_size,
                        })
                except (PermissionError, OSError):
                    continue
            
            lines = [f"Downloads folder analysis:"]
            lines.append(f"  Total: {total_files} files, {self._get_file_size_str(total_size)}")
            
            if old_files:
                old_size = sum(f['size'] for f in old_files)
                lines.append(f"\n  📦 {len(old_files)} files older than 30 days ({self._get_file_size_str(old_size)}):")
                for f in sorted(old_files, key=lambda x: x['size'], reverse=True)[:5]:
                    lines.append(f"    - {f['name']} ({self._get_file_size_str(f['size'])})")
                if len(old_files) > 5:
                    lines.append(f"    ... and {len(old_files) - 5} more")
            
            if large_files:
                lines.append(f"\n  📁 {len(large_files)} large files (>100MB):")
                for f in sorted(large_files, key=lambda x: x['size'], reverse=True):
                    lines.append(f"    - {f['name']} ({self._get_file_size_str(f['size'])})")
            
            lines.append(f"\n  💡 Tip: Say 'organize downloads' to sort files into category folders")
            if old_files:
                lines.append(f"  💡 Tip: Say 'delete file [name]' to remove old files (goes to Recycle Bin)")
            
            logger.info(f"Downloads analysis: {total_files} files, {len(old_files)} old, {len(large_files)} large")
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"Error analyzing downloads: {e}")
            return f"Error analyzing downloads: {str(e)}"
    
    def bulk_rename(self, location: str, pattern: str, replacement: str, file_type: str = "") -> str:
        """
        Bulk rename files in a directory using find-and-replace on filenames.
        
        Args:
            location: Directory containing files to rename
            pattern: Text pattern to find in filenames
            replacement: Text to replace the pattern with
            file_type: Optional file extension filter (e.g., 'jpg', 'txt')
            
        Returns:
            str: Rename report
        """
        try:
            target_dir = self._resolve_user_path(location)
            
            if not target_dir.exists():
                return f"Directory not found: {location}"
            
            valid, resolved, error = self._validate_path(str(target_dir))
            if not valid:
                return f"Cannot rename files: {error}"
            
            if not pattern:
                return "No search pattern provided"
            
            ext_filter = None
            if file_type:
                ext_filter = file_type.strip().lower()
                if not ext_filter.startswith('.'):
                    ext_filter = '.' + ext_filter
            
            renamed = 0
            failed = 0
            
            for item in sorted(target_dir.iterdir()):
                if not item.is_file():
                    continue
                
                if ext_filter and item.suffix.lower() != ext_filter:
                    continue
                
                if pattern.lower() not in item.stem.lower():
                    continue
                
                # Case-insensitive replacement in stem only
                import re
                new_stem = re.sub(re.escape(pattern), replacement, item.stem, flags=re.IGNORECASE)
                new_name = new_stem + item.suffix
                
                if new_name == item.name:
                    continue
                
                new_path = item.parent / new_name
                if new_path.exists():
                    failed += 1
                    continue
                
                try:
                    item.rename(new_path)
                    renamed += 1
                except Exception:
                    failed += 1
            
            if renamed == 0:
                if failed > 0:
                    return f"Could not rename {failed} files (name conflicts). No changes made."
                return f"No files matching '{pattern}' found in {target_dir.name}"
            
            result = f"Renamed {renamed} file{'s' if renamed > 1 else ''}: '{pattern}' → '{replacement}'"
            if failed:
                result += f" ({failed} skipped due to conflicts)"
            
            logger.info(f"Bulk rename in {target_dir}: {renamed} renamed, {failed} failed")
            return result
            
        except Exception as e:
            logger.error(f"Error bulk renaming: {e}")
            return f"Error bulk renaming: {str(e)}"
    
    # ========================================
    # COMPRESSION
    # ========================================
    
    def compress_files(self, source: str, archive_name: str = "") -> str:
        """
        Compress a file or folder into a ZIP archive.
        
        Args:
            source: File or folder path to compress
            archive_name: Optional name for the archive (default: same as source)
            
        Returns:
            str: Result message
        """
        try:
            valid, src_path, error = self._validate_path(source)
            if not valid:
                return f"Cannot compress: {error}"
            
            if not src_path.exists():
                return f"Source not found: {source}"
            
            # Determine archive path
            if archive_name:
                archive_name = archive_name.strip()
                if not archive_name.lower().endswith('.zip'):
                    archive_name += '.zip'
                zip_path = src_path.parent / archive_name
            else:
                zip_path = src_path.parent / f"{src_path.stem}.zip"
            
            # Handle name conflicts
            if zip_path.exists():
                stem = zip_path.stem
                counter = 1
                while zip_path.exists():
                    zip_path = zip_path.parent / f"{stem} ({counter}).zip"
                    counter += 1
            
            file_count = 0
            original_size = 0
            
            with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                if src_path.is_file():
                    zf.write(str(src_path), src_path.name)
                    file_count = 1
                    original_size = src_path.stat().st_size
                else:
                    # Compress directory
                    for item in src_path.rglob('*'):
                        if item.is_file():
                            arcname = item.relative_to(src_path)
                            zf.write(str(item), str(arcname))
                            file_count += 1
                            original_size += item.stat().st_size
            
            zip_size = zip_path.stat().st_size
            ratio = (1 - zip_size / original_size) * 100 if original_size > 0 else 0
            
            logger.info(f"Compressed {file_count} files: {src_path} -> {zip_path}")
            return (
                f"Created archive '{zip_path.name}' with {file_count} file{'s' if file_count > 1 else ''}. "
                f"Size: {self._get_file_size_str(zip_size)} "
                f"(compressed {ratio:.0f}% from {self._get_file_size_str(original_size)})"
            )
            
        except Exception as e:
            logger.error(f"Error compressing: {e}")
            return f"Error compressing files: {str(e)}"
    
    def extract_archive(self, archive_path: str, destination: str = "") -> str:
        """
        Extract a ZIP archive.
        
        Args:
            archive_path: Path to the ZIP file
            destination: Optional extraction directory (default: same as archive)
            
        Returns:
            str: Result message
        """
        try:
            valid, zip_path, error = self._validate_path(archive_path)
            if not valid:
                return f"Cannot extract: {error}"
            
            if not zip_path.exists():
                return f"Archive not found: {archive_path}"
            
            if not zipfile.is_zipfile(str(zip_path)):
                return f"'{zip_path.name}' is not a valid ZIP archive"
            
            # Determine extraction directory
            if destination:
                valid_dst, extract_dir, error = self._validate_path(destination)
                if not valid_dst:
                    return f"Invalid destination: {error}"
            else:
                extract_dir = zip_path.parent / zip_path.stem
            
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(str(zip_path), 'r') as zf:
                # Security check: prevent path traversal
                for info in zf.infolist():
                    if info.filename.startswith('/') or '..' in info.filename:
                        return "Archive contains unsafe paths. Extraction aborted for security."
                
                file_count = len(zf.infolist())
                zf.extractall(str(extract_dir))
            
            total_size = sum(
                f.stat().st_size for f in extract_dir.rglob('*') if f.is_file()
            )
            
            logger.info(f"Extracted {file_count} items from {zip_path} to {extract_dir}")
            return (
                f"Extracted {file_count} item{'s' if file_count > 1 else ''} "
                f"to '{extract_dir.name}' ({self._get_file_size_str(total_size)})"
            )
            
        except zipfile.BadZipFile:
            return f"'{archive_path}' is corrupted or not a valid ZIP file"
        except Exception as e:
            logger.error(f"Error extracting archive: {e}")
            return f"Error extracting archive: {str(e)}"
    
    # ========================================
    # FILE INFO
    # ========================================
    
    def get_file_info(self, file_path: str) -> str:
        """
        Get detailed information about a file or folder.
        
        Args:
            file_path: Path to the file or folder
            
        Returns:
            str: File information
        """
        try:
            path = self._resolve_user_path(file_path)
            
            if not path.exists():
                return f"File not found: {file_path}"
            
            stat = path.stat()
            
            if path.is_file():
                info = [f"File: {path.name}"]
                info.append(f"  Location: {path.parent}")
                info.append(f"  Size: {self._get_file_size_str(stat.st_size)}")
                info.append(f"  Type: {path.suffix.upper()[1:] if path.suffix else 'Unknown'}")
                info.append(f"  Created: {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M')}")
                info.append(f"  Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}")
                
                # Check if it's read-only
                if not os.access(str(path), os.W_OK):
                    info.append(f"  ⚠ Read-only")
                    
            else:
                # Directory info
                file_count = 0
                dir_count = 0
                total_size = 0
                
                try:
                    for item in path.rglob('*'):
                        if item.is_file():
                            file_count += 1
                            total_size += item.stat().st_size
                        elif item.is_dir():
                            dir_count += 1
                except PermissionError:
                    pass
                
                info = [f"Folder: {path.name}"]
                info.append(f"  Location: {path.parent}")
                info.append(f"  Contains: {file_count} files, {dir_count} subfolders")
                info.append(f"  Total size: {self._get_file_size_str(total_size)}")
                info.append(f"  Created: {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M')}")
                info.append(f"  Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}")
            
            return '\n'.join(info)
            
        except PermissionError:
            return f"Permission denied accessing '{file_path}'"
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return f"Error getting file info: {str(e)}"
    
    def list_folder(self, location: str = "downloads", sort_by: str = "name") -> str:
        """
        List contents of a folder with details.
        
        Args:
            location: Directory to list (default: Downloads)
            sort_by: Sort order - 'name', 'size', 'date' (default: name)
            
        Returns:
            str: Folder listing
        """
        try:
            target_dir = self._resolve_user_path(location)
            
            if not target_dir.exists():
                return f"Directory not found: {location}"
            
            items = []
            for item in target_dir.iterdir():
                if item.name.startswith('.'):
                    continue
                try:
                    stat = item.stat()
                    items.append({
                        'name': item.name,
                        'is_dir': item.is_dir(),
                        'size': stat.st_size if item.is_file() else 0,
                        'modified': stat.st_mtime,
                    })
                except (PermissionError, OSError):
                    continue
            
            if not items:
                return f"{target_dir.name} is empty"
            
            # Sort
            if sort_by == 'size':
                items.sort(key=lambda x: x['size'], reverse=True)
            elif sort_by == 'date':
                items.sort(key=lambda x: x['modified'], reverse=True)
            else:
                # Folders first, then files, alphabetical
                items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            dirs = [i for i in items if i['is_dir']]
            files = [i for i in items if not i['is_dir']]
            
            lines = [f"Contents of {target_dir.name} ({len(dirs)} folders, {len(files)} files):"]
            
            for item in items[:40]:  # Limit output
                if item['is_dir']:
                    lines.append(f"  📁 {item['name']}/")
                else:
                    size = self._get_file_size_str(item['size'])
                    lines.append(f"  📄 {item['name']} ({size})")
            
            if len(items) > 40:
                lines.append(f"  ... and {len(items) - 40} more items")
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"Error listing folder: {e}")
            return f"Error listing folder: {str(e)}"
