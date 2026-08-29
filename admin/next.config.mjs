/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_ADMIN_BASE_PATH || '/administracao';

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Servido pelo LiteSpeed sob /administracao em prod; direto na :3001 em dev.
  basePath,
  transpilePackages: ['@ecom/ui'],
  env: {
    NEXT_PUBLIC_ADMIN_BASE_PATH: basePath,
  },
};

export default nextConfig;
