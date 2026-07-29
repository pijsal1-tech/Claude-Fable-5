# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  Path Policy Helper — resolve_workspace_path
  
  Centralized verification for path containment, symlink
  prevention, and secrets denylist checks.
═══════════════════════════════════════════════════════
"""
import logging
import os
import pathlib
from typing import Set

_LOG = logging.getLogger("chain.path_policy")

SECRETS_DENYLIST_NAMES: Set[str] = {
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "credentials", "passwd", "shadow", "keys.txt"
}
SECRETS_DENYLIST_EXTENSIONS: Set[str] = {
    ".pem", ".key", ".pkcs12", ".pfx", ".p12", ".asc"
}
SECRETS_DENYLIST_DIRS: Set[str] = {
    ".aws", ".ssh", ".git", ".gcloud", ".kube"
}

def is_secret_file(path: pathlib.Path) -> bool:
    """Checks if a path matches any secrets pattern or directory name."""
    name_lower = path.name.lower()
    
    # Allow .env.example, but block .env or .env.local, etc.
    if name_lower == ".env.example":
        return False
    if name_lower == ".env" or name_lower.startswith(".env."):
        return True
        
    if name_lower in SECRETS_DENYLIST_NAMES:
        return True
        
    if path.suffix.lower() in SECRETS_DENYLIST_EXTENSIONS:
        return True
        
    for part in path.parts:
        part_lower = part.lower()
        if part_lower in SECRETS_DENYLIST_DIRS:
            return True
        # also match directories like .ssh or .aws hidden directories
        if part_lower.startswith(".") and part_lower[1:] in {"aws", "ssh", "git", "gcloud", "kube"}:
            return True
            
    return False

def resolve_workspace_path(
    root: str | pathlib.Path,
    requested_path: str,
    must_exist: bool = False,
    allow_symlinks: bool = False
) -> pathlib.Path:
    """
    Safely resolves a requested path under the workspace root.
    Ensures containment, symlink checks, and secrets denylist enforcement.
    """
    root_path = pathlib.Path(root).resolve()
    
    # Handle empty/default paths
    if not requested_path:
        requested_path = "."
        
    p = pathlib.Path(requested_path)
    if p.is_absolute():
        raw_path = p
    else:
        raw_path = root_path / p
        
    # Resolve absolute path to canonical form
    try:
        resolved_path = raw_path.resolve()
    except Exception:
        resolved_path = raw_path.absolute()
        
    # Standardize separator and case comparison on Windows
    if os.name == 'nt':
        r_parts = [part.lower() for part in root_path.parts]
        f_parts = [part.lower() for part in resolved_path.parts]
        if len(f_parts) < len(r_parts) or f_parts[:len(r_parts)] != r_parts:
            raise PermissionError(
                f"Access denied: path '{requested_path}' resolves to '{resolved_path}' "
                f"which is outside project root '{root_path}'."
            )
    else:
        try:
            resolved_path.relative_to(root_path)
        except ValueError:
            raise PermissionError(
                f"Access denied: path '{requested_path}' resolves to '{resolved_path}' "
                f"which is outside project root '{root_path}'."
            )
            
    # Symlink traversal check
    # TSK-618 (ASF-07/NF-28): فصل القياس عن القرار — النسخة السابقة
    # وضعت raise PermissionError داخل try يلتقط Exception واسعًا
    # (PermissionError ⊂ OSError ⊂ Exception) فكان الرفض نفسه يُبتلع
    # والفحص ميتًا بالكامل. الآن: is_symlink وحده داخل try ضيق
    # يلتقط OSError موسومًا بتحذير (لا تخطٍّ صامت)؛ الرفض خارجه.
    if not allow_symlinks:
        curr = raw_path
        # Traverse upwards checking if any part of the requested path is a symlink
        while curr != root_path and len(curr.parts) > len(root_path.parts):
            try:
                is_link = curr.is_symlink()
            except OSError as e:
                _LOG.warning(
                    "symlink check failed for %r (segment of %r): %s — "
                    "segment skipped; final containment and secrets "
                    "checks still apply",
                    str(curr), requested_path, e)
                is_link = False
            if is_link:
                raise PermissionError(
                    f"Access denied: Symlinks are not allowed: '{requested_path}'"
                )
            curr = curr.parent
            
    # Secrets denylist check
    if is_secret_file(resolved_path):
        raise PermissionError(
            f"Access denied: '{requested_path}' matches blocked secret patterns."
        )
        
    if must_exist and not resolved_path.exists():
        raise FileNotFoundError(f"File not found: '{requested_path}'")
        
    return resolved_path
