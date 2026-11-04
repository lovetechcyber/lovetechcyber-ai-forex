
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),

    VitePWA({
      registerType: 'autoUpdate',

      includeAssets: [
        'icons/icon-192.png',
        'icons/icon-512.png',
      ],

      manifest: {
        id: '/',
        name: 'LovetechCyber AI Forex Analyst',
        short_name: 'Lovetech Forex',
        description:
          'AI-powered forex market analysis, market structure and multi-timeframe intelligence.',

        theme_color: '#0b1220',
        background_color: '#0b1220',
        display: 'standalone',
        orientation: 'any',
        start_url: '/',

        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any',
          },
        ],
      },

      workbox: {
        navigateFallback: '/index.html',

        globPatterns: [
          '**/*.{js,css,html,ico,png,svg,woff2}',
        ],

        runtimeCaching: [
          {
            urlPattern: ({ url }) =>
              url.pathname.startsWith('/api/'),

            handler: 'NetworkOnly',
          },
        ],
      },

      devOptions: {
        enabled: true,
        type: 'module',
      },
    }),
  ],

  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})
