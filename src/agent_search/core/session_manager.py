"""
Session Persistence Manager

Manages cookies and session state across requests to maintain
consistency and avoid detection.
"""

import os
import json
import pickle
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta


class SessionManager:
    """
    Manages persistent sessions with cookie storage.
    
    Usage:
        manager = SessionManager()
        
        # Get a session for a domain
        session = manager.get_session("example.com")
        
        # Use the session
        response = session.get("https://example.com/page")
        
        # Cookies are automatically persisted
        manager.save_session("example.com", session)
    """
    
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        session_ttl: int = 3600,  # 1 hour default
    ):
        """
        Initialize session manager.
        
        Args:
            storage_dir: Directory to store session files (default: ~/.cache/agent-search/sessions)
            session_ttl: Session time-to-live in seconds
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path.home() / ".cache" / "agent-search" / "sessions"
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.session_ttl = session_ttl
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
    def _get_session_file(self, domain: str) -> Path:
        """Get the file path for a domain's session."""
        safe_domain = domain.replace('/', '_').replace(':', '_')
        return self.storage_dir / f"{safe_domain}.pkl"
    
    def _get_metadata_file(self, domain: str) -> Path:
        """Get the file path for a domain's session metadata."""
        safe_domain = domain.replace('/', '_').replace(':', '_')
        return self.storage_dir / f"{safe_domain}.json"
    
    def get_session(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Load a session for a domain.
        
        Args:
            domain: The domain to get session for
            
        Returns:
            Session data dict or None if not found/expired
        """
        # Check memory cache first
        if domain in self._sessions:
            session_data = self._sessions[domain]
            if not self._is_expired(session_data):
                return session_data
            else:
                del self._sessions[domain]
        
        # Try to load from disk
        session_file = self._get_session_file(domain)
        metadata_file = self._get_metadata_file(domain)
        
        if not session_file.exists() or not metadata_file.exists():
            return None
        
        try:
            # Check if expired
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            last_accessed = datetime.fromisoformat(metadata.get('last_accessed', '1970-01-01'))
            if datetime.now() - last_accessed > timedelta(seconds=self.session_ttl):
                # Session expired, clean up
                session_file.unlink(missing_ok=True)
                metadata_file.unlink(missing_ok=True)
                return None
            
            # Load session data
            with open(session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            # Update cache
            self._sessions[domain] = session_data
            return session_data
            
        except Exception:
            # Failed to load, clean up
            session_file.unlink(missing_ok=True)
            metadata_file.unlink(missing_ok=True)
            return None
    
    def save_session(self, domain: str, session_data: Dict[str, Any]):
        """
        Save a session for a domain.
        
        Args:
            domain: The domain to save session for
            session_data: Session data to save
        """
        # Update cache
        session_data['_last_saved'] = datetime.now().isoformat()
        self._sessions[domain] = session_data
        
        # Save to disk
        session_file = self._get_session_file(domain)
        metadata_file = self._get_metadata_file(domain)
        
        try:
            with open(session_file, 'wb') as f:
                pickle.dump(session_data, f)
            
            metadata = {
                'domain': domain,
                'last_accessed': datetime.now().isoformat(),
                'ttl': self.session_ttl,
            }
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)
                
        except Exception as e:
            print(f"Failed to save session for {domain}: {e}")
    
    def _is_expired(self, session_data: Dict[str, Any]) -> bool:
        """Check if a session has expired."""
        last_saved = session_data.get('_last_saved')
        if not last_saved:
            return True
        
        try:
            last_saved_dt = datetime.fromisoformat(last_saved)
            return datetime.now() - last_saved_dt > timedelta(seconds=self.session_ttl)
        except:
            return True
    
    def delete_session(self, domain: str):
        """Delete a session for a domain."""
        if domain in self._sessions:
            del self._sessions[domain]
        
        session_file = self._get_session_file(domain)
        metadata_file = self._get_metadata_file(domain)
        
        session_file.unlink(missing_ok=True)
        metadata_file.unlink(missing_ok=True)
    
    def list_sessions(self) -> list:
        """List all stored sessions."""
        sessions = []
        for metadata_file in self.storage_dir.glob('*.json'):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    sessions.append(metadata)
            except:
                pass
        return sessions
    
    def clear_expired(self):
        """Clear all expired sessions."""
        for metadata_file in self.storage_dir.glob('*.json'):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                last_accessed = datetime.fromisoformat(metadata.get('last_accessed', '1970-01-01'))
                ttl = metadata.get('ttl', self.session_ttl)
                
                if datetime.now() - last_accessed > timedelta(seconds=ttl):
                    # Expired, delete files
                    domain = metadata.get('domain', '')
                    session_file = self._get_session_file(domain)
                    metadata_file.unlink(missing_ok=True)
                    session_file.unlink(missing_ok=True)
                    
                    if domain in self._sessions:
                        del self._sessions[domain]
                        
            except:
                pass
    
    def clear_all(self):
        """Clear all sessions."""
        for file in self.storage_dir.glob('*.pkl'):
            file.unlink(missing_ok=True)
        for file in self.storage_dir.glob('*.json'):
            file.unlink(missing_ok=True)
        self._sessions.clear()


class CookieManager:
    """
    Manages cookies for HTTP requests.
    
    Usage:
        cookie_manager = CookieManager()
        
        # Get cookies for a request
        cookies = cookie_manager.get_cookies("example.com")
        
        # Update cookies from response
        cookie_manager.update_cookies("example.com", response.cookies)
    """
    
    def __init__(self, session_manager: Optional[SessionManager] = None):
        self.session_manager = session_manager or SessionManager()
        self._cookie_cache: Dict[str, Dict[str, Any]] = {}
    
    def get_cookies(self, domain: str) -> Dict[str, str]:
        """
        Get cookies for a domain.
        
        Args:
            domain: The domain to get cookies for
            
        Returns:
            Dictionary of cookie name -> value
        """
        # Check cache
        if domain in self._cookie_cache:
            return self._cookie_cache[domain]
        
        # Load from session
        session = self.session_manager.get_session(domain)
        if session and 'cookies' in session:
            self._cookie_cache[domain] = session['cookies']
            return session['cookies']
        
        return {}
    
    def update_cookies(self, domain: str, cookies: Any):
        """
        Update cookies for a domain.
        
        Args:
            domain: The domain to update cookies for
            cookies: New cookies (dict or requests cookie jar)
        """
        # Convert requests cookie jar to dict
        if hasattr(cookies, 'get_dict'):
            cookies = cookies.get_dict()
        elif not isinstance(cookies, dict):
            cookies = dict(cookies)
        
        # Get existing cookies
        existing = self.get_cookies(domain)
        
        # Merge
        existing.update(cookies)
        
        # Update cache
        self._cookie_cache[domain] = existing
        
        # Save to session
        session = self.session_manager.get_session(domain) or {}
        session['cookies'] = existing
        self.session_manager.save_session(domain, session)
    
    def clear_cookies(self, domain: str):
        """Clear cookies for a domain."""
        if domain in self._cookie_cache:
            del self._cookie_cache[domain]
        
        session = self.session_manager.get_session(domain)
        if session:
            session.pop('cookies', None)
            self.session_manager.save_session(domain, session)
    
    def clear_all_cookies(self):
        """Clear all cookies."""
        self._cookie_cache.clear()
        # This will clear all sessions including cookies
        self.session_manager.clear_all()
