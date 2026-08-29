/** @type {import('next').NextConfig} */
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const { hostname, protocol, port } = new URL(apiUrl);

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // `@ecom/ui` é consumido como TS/TSX cru via workspace — o Next transpila.
  transpilePackages: ['@ecom/ui'],
  images: {
    // Mídia servida pela API (WebP + thumb/medium/zoom). Loader real entra na Fase 3.
    remotePatterns: [
      {
        protocol: protocol.replace(':', ''),
        hostname,
        port: port || undefined,
        pathname: '/media/**',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
          { key: 'Service-Worker-Allowed', value: '/' },
        ],
      },
    ];
  },
};

export default nextConfig;
