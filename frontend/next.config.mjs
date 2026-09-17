/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The emergency content must be available offline, so it is bundled rather
  // than fetched. Day 4: add a service worker to cache the shell itself.
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:3000',
  },
};

export default nextConfig;
