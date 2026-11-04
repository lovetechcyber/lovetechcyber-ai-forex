# LovetechCyber AI Forex Analyst

An MT5-connected forex market analysis platform with a responsive
React dashboard, Python backend, MongoDB database, hosted AI
explanations, and historical backtesting.

## Technology stack

- Frontend: React, TypeScript, Tailwind CSS
- Backend: Python, FastAPI
- Database: MongoDB
- MT5 integration: MQL5 Expert Advisor
- AI: Hosted model through a server-side API
- Mobile: Responsive web application / PWA
- Backtesting: Historical replay and signal evaluation

## Initial scope

- Continuous market monitoring while MT5 is running
- Broker-supported forex symbols
- M5, M15, M30, H1, H4 and D1 timeframes
- Technical indicators and multi-timeframe analysis
- Liquidity zones, breakouts and false-breakout detection
- Personalized analysis settings and alerts
- AI-generated explanations grounded in calculated results
- Historical backtesting
- Mobile-friendly analysis dashboard

## Development principles

1. Keep quantitative calculations separate from AI explanations.
2. Validate market data before analysis.
3. Do not use future information in historical replay.
4. Never expose AI provider credentials to the frontend or EA.
5. Do not implement live trade execution in the initial release.
6. Monitor data freshness, connector health and failed uploads.

## Repository structure

- `apps/web`: React web application
- `apps/mobile`: optional future native mobile application
- `integrations/mt5-ea`: MQL5 Expert Advisor and modules
- `services/api`: FastAPI backend
- `services/market-data`: market data validation and normalization
- `services/analysis-engine`: quantitative analysis
- `services/ai-service`: hosted AI integration
- `services/backtester`: historical replay and evaluation
- `services/notifications`: alerts and notifications
- `services/scheduler`: scheduled analysis jobs
- `packages/contracts`: shared API contracts
- `database`: migrations and schema documentation
- `tests`: automated tests
- `infra`: deployment configuration

## Getting started

This repository contains the initial folder structure and placeholders.
Application dependencies and service implementations must be added
as development progresses.

1. Install Git, Python, Node.js and Docker Desktop.
2. Create a Python virtual environment for the backend.
3. Configure the frontend with React, TypeScript and Tailwind CSS.
4. Start MongoDB using Docker Compose.
5. Implement the API and the MQL5 market-data connector.
6. Configure MT5 to allow HTTPS requests to the API host.
7. Test against a demo terminal before deploying.

## Safety

The initial product is analysis-only. It must not submit, modify,
or close trading orders.
