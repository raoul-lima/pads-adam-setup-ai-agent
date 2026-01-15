'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import LoginForm from '@/components/LoginForm';
import { validateCredentials, LoginCredentials } from '@/lib/auth';

export default function LoginPage() {
  const [error, setError] = useState<string>('');
  const router = useRouter();

  const handleLogin = async (credentials: LoginCredentials) => {
    setError('');
    
    if (validateCredentials(credentials)) {
      // Set authentication cookie
      document.cookie = 'admin-session=authenticated; path=/; max-age=86400; secure; samesite=strict';
      router.push('/dashboard');
    } else {
      setError('Invalid username or password');
    }
  };

  return <LoginForm onLogin={handleLogin} error={error} />;
}
