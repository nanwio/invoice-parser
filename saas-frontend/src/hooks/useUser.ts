import { useUser as useClerkUser } from '@clerk/nextjs';
import { useEffect, useState } from 'react';
import { supabase, dbHelpers } from '@/lib/supabase';
import { User } from '@/types';

export function useUser() {
  const { user: clerkUser, isLoaded } = useClerkUser();
  const [dbUser, setDbUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function syncUser() {
      if (!isLoaded) return;

      if (!clerkUser) {
        setDbUser(null);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const user = await dbHelpers.getOrCreateUser(
          clerkUser.id,
          clerkUser.emailAddresses[0]?.emailAddress || ''
        );

        setDbUser(user);
      } catch (err) {
        console.error('Failed to sync user:', err);
        setError(err instanceof Error ? err.message : 'Failed to sync user');
      } finally {
        setLoading(false);
      }
    }

    syncUser();
  }, [clerkUser, isLoaded]);

  return {
    clerkUser,
    dbUser,
    loading,
    error,
    isAuthenticated: !!clerkUser && !!dbUser,
  };
}