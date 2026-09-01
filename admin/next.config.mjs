/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_ADMIN_BASE_PATH || '/administracao';

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Some o selo flutuante do Next (logo "N") no canto da página em dev.
  devIndicators: false,
  // Permite abrir o dev server pelo IP da máquina na LAN (teste no celular).
  allowedDevOrigins: ['192.168.100.23'],
  // Servido pelo LiteSpeed sob /administracao em prod; direto na :3001 em dev.
  basePath,
  transpilePackages: ['@ecom/ui'],
  env: {
    NEXT_PUBLIC_ADMIN_BASE_PATH: basePath,
  },
  // Aceita também /admin como atalho para /administracao (basePath real).
  async redirects() {
    if (basePath === '/admin') return [];
    return [
      { source: '/admin', destination: basePath, basePath: false, permanent: false },
      { source: '/admin/:path*', destination: `${basePath}/:path*`, basePath: false, permanent: false },
    ];
  },
};

export default nextConfig;
