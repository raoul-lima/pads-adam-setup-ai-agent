'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

export default function Home() {
  const router = useRouter();
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    // Start fade out after a short delay
    const fadeOutTimer = setTimeout(() => {
      setIsFadingOut(true);
    }, 1500); // 1.5 second spin

    // Redirect after fade out animation completes
    const redirectTimer = setTimeout(() => {
      router.push('/chat');
    }, 2000); // 1.5s spin + 0.5s fade

    return () => {
      clearTimeout(fadeOutTimer);
      clearTimeout(redirectTimer);
    };
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--card-background)]">
      <div className={`text-center transition-opacity duration-500 ${isFadingOut ? 'animate-fade-out' : 'opacity-100'}`}>
        <div className="relative h-32 w-32 mx-auto">
          <Image 
            src="/adsecura_logo.png" 
            alt="Loading Adsecura Logo" 
            layout="fill" 
            objectFit="contain" 
            className="animate-spin" 
            style={{ animationDuration: '1.5s' }}
          />
        </div>
        <p className="mt-4 text-[var(--text-secondary)]">Loading Adam Setup Agent...</p>
      </div>
    </div>
  );
}
