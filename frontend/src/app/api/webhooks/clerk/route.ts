import { headers } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';
import { Webhook } from 'svix';
import { supabaseAdmin } from '@/lib/supabase';

const webhookSecret = process.env.CLERK_WEBHOOK_SECRET;

export async function POST(req: NextRequest) {
  if (!webhookSecret) {
    throw new Error('CLERK_WEBHOOK_SECRET is not set');
  }

  // Get the headers
  const headerPayload = headers();
  const svix_id = headerPayload.get('svix-id');
  const svix_timestamp = headerPayload.get('svix-timestamp');
  const svix_signature = headerPayload.get('svix-signature');

  // If there are no headers, error out
  if (!svix_id || !svix_timestamp || !svix_signature) {
    return new NextResponse('Error occured -- no svix headers', {
      status: 400,
    });
  }

  // Get the body
  const payload = await req.json();
  const body = JSON.stringify(payload);

  // Create a new Svix instance with your secret.
  const wh = new Webhook(webhookSecret);

  let evt: any;

  // Verify the payload with the headers
  try {
    evt = wh.verify(body, {
      'svix-id': svix_id,
      'svix-timestamp': svix_timestamp,
      'svix-signature': svix_signature,
    });
  } catch (err) {
    console.error('Error verifying webhook:', err);
    return new NextResponse('Error occured', {
      status: 400,
    });
  }

  // Handle the webhook
  const eventType = evt.type;
  console.log(`Webhook with an ID of ${evt.data.id} and type of ${eventType}`);

  try {
    switch (eventType) {
      case 'user.created':
        await handleUserCreated(evt.data);
        break;
      case 'user.updated':
        await handleUserUpdated(evt.data);
        break;
      case 'user.deleted':
        await handleUserDeleted(evt.data);
        break;
      default:
        console.log('Unhandled webhook event type:', eventType);
    }

    return new NextResponse('OK', { status: 200 });
  } catch (error) {
    console.error('Error handling webhook:', error);
    return new NextResponse('Error processing webhook', { status: 500 });
  }
}

async function handleUserCreated(userData: any) {
  const email = userData.email_addresses?.[0]?.email_address;

  if (!email) {
    console.error('No email found for user:', userData.id);
    return;
  }

  const { data, error } = await supabaseAdmin
    .from('users')
    .insert([
      {
        clerk_user_id: userData.id,
        email: email,
        plan_type: 'free',
      },
    ])
    .select()
    .single();

  if (error) {
    console.error('Error creating user in Supabase:', error);
    throw error;
  }

  console.log('User created in Supabase:', data);
}

async function handleUserUpdated(userData: any) {
  const email = userData.email_addresses?.[0]?.email_address;

  if (!email) {
    console.error('No email found for user:', userData.id);
    return;
  }

  const { data, error } = await supabaseAdmin
    .from('users')
    .update({
      email: email,
      updated_at: new Date().toISOString(),
    })
    .eq('clerk_user_id', userData.id)
    .select()
    .single();

  if (error) {
    console.error('Error updating user in Supabase:', error);
    throw error;
  }

  console.log('User updated in Supabase:', data);
}

async function handleUserDeleted(userData: any) {
  const { error } = await supabaseAdmin
    .from('users')
    .delete()
    .eq('clerk_user_id', userData.id);

  if (error) {
    console.error('Error deleting user from Supabase:', error);
    throw error;
  }

  console.log('User deleted from Supabase:', userData.id);
}