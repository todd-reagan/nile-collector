/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: 'export',
  distDir: 'out',
  images: {
    unoptimized: true,
  },
  env: {
    // These values will be replaced during deployment
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://api.example.com',
    NEXT_PUBLIC_REGION: process.env.NEXT_PUBLIC_REGION || 'us-west-2',
    NEXT_PUBLIC_USER_POOL_ID: process.env.NEXT_PUBLIC_USER_POOL_ID || 'us-west-2_xxxxxxxx',
    NEXT_PUBLIC_USER_POOL_CLIENT_ID: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID || 'xxxxxxxxxxxxxxxxxxxxxxxxxx',
  },
  // Removed rewrites configuration as it's incompatible with static export
};

module.exports = nextConfig;
