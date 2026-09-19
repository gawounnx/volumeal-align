/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three'],
  async rewrites() {
    const backend = (process.env.API_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
    return [{ source: '/api/v1/:path*', destination: `${backend}/api/v1/:path*` }];
  },
};
export default nextConfig;
