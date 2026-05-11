import { useState, useRef, useEffect } from 'react';
import { ChevronDown, LogOut, User as UserIcon } from 'lucide-react';

interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
}

interface UserDropdownProps {
  user: User;
  onLogout: () => Promise<void>;
}

export function UserDropdown({ user, onLogout }: UserDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setIsOpen(false);
    await onLogout();
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)} 
        className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-white text-sm font-medium">
          {user.avatar_url ? (
            <img 
              src={user.avatar_url} 
              alt={user.name} 
              className="w-8 h-8 rounded-full object-cover"
            />
          ) : (
            <UserIcon className="w-4 h-4" />
          )}
        </div>
        <div className="hidden md:block text-left">
          <div className="text-sm font-medium text-gray-900 truncate max-w-[120px]">
            {user.name}
          </div>
          <div className="text-xs text-gray-500 truncate max-w-[120px]">
            {user.email}
          </div>
        </div>
        <ChevronDown className="w-4 h-4 text-gray-400" />
      </button>
      
      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
          <div className="px-4 py-3 border-b border-gray-100">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-white">
                {user.avatar_url ? (
                  <img 
                    src={user.avatar_url} 
                    alt={user.name} 
                    className="w-10 h-10 rounded-full object-cover"
                  />
                ) : (
                  <UserIcon className="w-5 h-5" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 truncate">{user.name}</div>
                <div className="text-sm text-gray-500 truncate">{user.email}</div>
              </div>
            </div>
          </div>
          
          <button
            onClick={handleLogout}
            className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center space-x-2"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </div>
  );
}