# PostBot Frontend (Next.js)

A modern, production-ready web application for generating high-quality LinkedIn posts from GitHub activity using AI.

## Features

- **AI-Powered Generation**: Create engaging posts from your code commits using Groq, OpenAI (Pro), Anthropic (Pro), or Mistral (Pro).
- **GitHub Integration**: Automatically scan and visualize your recent coding activity.
- **Smart Dashboard**:
  - **Activity Feed**: View and select commits to post about.
  - **Stats Overview**: Track your generation and publishing metrics.
  - **Post Queue**: Manage, edit, and schedule drafted posts.
  - **Bot Mode Panel**: One-click scan → generate → review → publish workflow.
  - **AI Status Messages**: Personalised chat-bubble feedback with typewriter animation during all operations.
- **Post Scheduling**: Schedule posts for future publication via Celery + Redis.
- **Persona System**: AI writing persona quiz that tailors post tone and style.
- **Premium UX**:
  - **Skeleton Loading**: Smooth loading states for all data-heavy components.
  - **Dark Mode**: System-aware dark theme with flash prevention.
  - **Responsive Design**: Optimized for mobile and desktop.
  - **Focus Trapping**: Full keyboard accessibility in modals.
  - **ARIA Support**: Proper labels, roles, and associations throughout.
  - **Glassmorphism Auth Pages**: Redesigned sign-up/sign-in with gradient panels and trust signals.
- **Secure Authentication**: Powered by Clerk for robust user management.
- **Payments**: Paystack integration with free/pro/enterprise tiers.

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.2 | Framework (Pages Router) |
| React | 18.3 | UI library |
| TypeScript | 5.9 | Type safety |
| Tailwind CSS | 3.4 | Styling |
| TanStack Query | 5.90 | Server state management |
| Clerk | 6.36 | Authentication |
| Axios | 1.13 | HTTP client (centralized `api` utility) |
| Jest | 29.7 | Testing |

## Project Structure

```
web/
├── src/
│   ├── components/
│   │   ├── dashboard/    # Dashboard widgets (11 components)
│   │   ├── modals/       # Dialog components (5 modals)
│   │   ├── settings/     # Persona quiz & settings
│   │   ├── ui/           # Reusable primitives (20 components, incl. AIStatusMessage)
│   │   └── landing/      # Landing page sections
│   ├── hooks/            # Custom React hooks
│   │   ├── useDashboardData.ts   # Data fetching
│   │   ├── useFocusTrap.ts       # Modal focus trapping
│   │   └── useKeyboardShortcuts.tsx
│   ├── lib/              # API client, toast utility
│   ├── pages/            # Next.js routes (15+ pages)
│   ├── types/            # TypeScript definitions
│   └── styles/           # Global styles and Tailwind directives
├── __tests__/            # Jest test suite (17+ tests)
├── public/               # Static assets
└── shared/contracts/     # Auto-generated OpenAPI types
```

## Quick Start

1. **Install Dependencies**

   ```bash
   npm install
   ```

2. **Configure Environment**

   Create `.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
   CLERK_SECRET_KEY=sk_test_...
   ```

3. **Run Development Server**

   ```bash
   npm run dev
   ```

4. **Run Tests**

   ```bash
   npm test
   ```

5. **Build for Production**

   ```bash
   npm run build
   ```

## API Type Generation

TypeScript types are auto-generated from the backend's OpenAPI spec:

```bash
# Ensure backend is running on :8000
npm run generate:types
```

Generated types are saved to `shared/contracts/index.d.ts` and imported in `src/types/dashboard.ts`.

## Security

- Secrets are never exposed in the client.
- API requests are authenticated via Clerk JWT tokens.
- Sensitive actions (API key management) are server-side only.
- CSP headers configured in `next.config.js`.

## Contributing

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
