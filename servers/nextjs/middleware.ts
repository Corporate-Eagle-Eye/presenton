import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Get feature toggles from environment
  const showDashboard = process.env.NEXT_PUBLIC_SHOW_DASHBOARD !== 'false';
  const showSettings = process.env.NEXT_PUBLIC_SHOW_SETTINGS !== 'false';
  
  // Suppress dashboard page if disabled
  if (pathname === '/dashboard' && !showDashboard) {
    return new NextResponse('Page not available', { status: 404 });
  }
  
  // Suppress settings page if disabled
  if (pathname === '/settings' && !showSettings) {
    return new NextResponse('Page not available', { status: 404 });
  }
  
  // Always allow presentation pages (core functionality)
  if (pathname.startsWith('/presentation')) {
    return NextResponse.next();
  }
  
  // Always allow API routes
  if (pathname.startsWith('/api')) {
    return NextResponse.next();
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard',
    '/presentation/:path*',
    '/api/:path*'
  ]
};
