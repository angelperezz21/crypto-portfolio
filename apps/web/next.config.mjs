/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // El frontend NUNCA llama directamente a Binance — solo a la API interna
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_URL ?? "http://api:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
