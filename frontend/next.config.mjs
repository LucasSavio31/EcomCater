/** @type {import('next').NextConfig} */
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const { hostname, protocol, port } = new URL(apiUrl);
const apiProtocol = protocol.replace(':', '');

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // `@ecom/ui` é consumido como TS/TSX cru via workspace — o Next transpila.
  transpilePackages: ['@ecom/ui'],
  images: {
    // Mídia servida pela API (WebP + thumb/medium/zoom) em `/media/...`.
    remotePatterns: [
      {
        protocol: apiProtocol === 'https' ? 'https' : 'http',
        hostname,
        port: port || undefined,
        pathname: '/media/**',
      },
      {
        protocol: apiProtocol === 'https' ? 'https' : 'http',
        hostname,
        port: port || undefined,
        pathname: '/static/**',
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
