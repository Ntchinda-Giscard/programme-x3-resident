// frontend/next.config.mjs
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",

  // CRITICAL: Use relative paths for assets
  assetPrefix: ".",

  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },

  // Add trailing slash
  trailingSlash: true,

  // Disable strict mode if you encounter issues
  reactStrictMode: true,

  // Webpack configuration for Electron
  // webpack: (config, { isServer }) => {
  //   if (!isServer) {
  //     config.target = "electron-renderer";
  //   }
  //   return config;
  // },
};

export default nextConfig; // ES Module syntax
