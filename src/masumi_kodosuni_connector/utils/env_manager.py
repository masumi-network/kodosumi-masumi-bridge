"""Environment file management utilities."""
import os
import re
from pathlib import Path
from typing import Optional, Dict, List
import tempfile
import shutil


class EnvManager:
    """Manage .env file modifications safely."""
    
    def __init__(self, env_path: Optional[Path] = None):
        """Initialize with .env file path."""
        if env_path is None:
            # Find .env file using same logic as settings.py
            import pathlib
            project_root = pathlib.Path(__file__).parent.parent.parent.parent.parent
            env_paths = [
                project_root / ".env",
                pathlib.Path.cwd() / ".env",
                pathlib.Path(".env")
            ]
            
            for path in env_paths:
                if path.exists():
                    self.env_path = path
                    break
            else:
                # Create .env in project root if none exists
                self.env_path = project_root / ".env"
        else:
            self.env_path = env_path
    
    def read_env_file(self) -> List[str]:
        """Read .env file lines."""
        if not self.env_path.exists():
            return []
        
        with open(self.env_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    
    def write_env_file(self, lines: List[str]) -> None:
        """Write .env file lines safely using atomic operation."""
        # Create a temporary file in the same directory
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.env_path.parent,
            prefix='.env.tmp.',
            text=True
        )
        
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                temp_file.writelines(lines)
            
            # Atomic move
            shutil.move(temp_path, self.env_path)
        except Exception:
            # Clean up temp file if something goes wrong
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    
    def set_agent_identifier(self, flow_key: str, identifier: Optional[str]) -> bool:
        """Set or remove an agent identifier in the .env file."""
        lines = self.read_env_file()
        env_key = f"AGENT_IDENTIFIER_{flow_key}"
        pattern = re.compile(rf'^#?\s*{re.escape(env_key)}\s*=.*$', re.MULTILINE)
        
        new_lines = []
        found = False
        
        for line in lines:
            if pattern.match(line.strip()):
                found = True
                if identifier:
                    # Enable agent
                    new_lines.append(f"{env_key}={identifier}\n")
                else:
                    # Disable agent (comment out)
                    new_lines.append(f"# {env_key}=\n")
            else:
                new_lines.append(line)
        
        # If not found and we want to enable, add it
        if not found and identifier:
            # Find a good place to add it (after other agent identifiers)
            agent_section_index = -1
            for i, line in enumerate(new_lines):
                if "AGENT_IDENTIFIER_" in line:
                    agent_section_index = i
            
            if agent_section_index >= 0:
                # Insert after the last agent identifier line
                new_lines.insert(agent_section_index + 1, f"{env_key}={identifier}\n")
            else:
                # Add at the end
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines.append('\n')
                new_lines.append(f"# Agent Configurations\n")
                new_lines.append(f"{env_key}={identifier}\n")
        
        try:
            self.write_env_file(new_lines)
            return True
        except Exception as e:
            print(f"Error updating .env file: {e}")
            return False
    
    def get_agent_identifier(self, flow_key: str) -> Optional[str]:
        """Get current agent identifier from .env file."""
        lines = self.read_env_file()
        env_key = f"AGENT_IDENTIFIER_{flow_key}"
        pattern = re.compile(rf'^{re.escape(env_key)}\s*=\s*(.*)$')
        
        for line in lines:
            match = pattern.match(line.strip())
            if match:
                value = match.group(1).strip()
                return value if value else None
        
        return None
    
    def is_agent_enabled(self, flow_key: str) -> bool:
        """Check if agent is enabled (not commented out and has value)."""
        identifier = self.get_agent_identifier(flow_key)
        return identifier is not None and identifier != ""