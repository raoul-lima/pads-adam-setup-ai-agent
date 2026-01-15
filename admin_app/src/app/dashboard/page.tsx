'use client';

import { useRouter } from 'next/navigation';
import FeedbackDashboard from '@/components/FeedbackDashboard';

export default function DashboardPage() {
  const router = useRouter();

  const handleLogout = () => {
    // Clear authentication cookie
    document.cookie = 'admin-session=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    router.push('/login');
  };

  return <FeedbackDashboard onLogout={handleLogout} />;
}
