// Jest setup file
// Add custom jest matchers for DOM testing
require('@testing-library/jest-dom');

// Polyfill structuredClone for jsdom
if (typeof globalThis.structuredClone === 'undefined') {
  globalThis.structuredClone = (val) => JSON.parse(JSON.stringify(val));
}

// Polyfill performance.markResourceTiming for jsdom (not available in all environments)
if (typeof performance !== 'undefined' && !performance.markResourceTiming) {
  performance.markResourceTiming = () => {};
}

// MSW requires these globals to be available.
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

const { ReadableStream, WritableStream, TransformStream } = require('stream/web');
global.ReadableStream = ReadableStream;
global.WritableStream = WritableStream;
global.TransformStream = TransformStream;

const { MessageChannel, MessagePort, BroadcastChannel } = require('worker_threads');
global.MessageChannel = MessageChannel;
global.MessagePort = MessagePort;
global.BroadcastChannel = BroadcastChannel;

// undici provides web-standard APIs that node 18+ has but jsdom doesn't expose globally by default.
// It must be required AFTER TextDecoder is polyfilled.
const { fetch, Headers, Request, Response, FormData } = require('undici');
global.fetch = fetch;
global.Headers = Headers;
global.Request = Request;
global.Response = Response;
global.FormData = FormData;

// Mock next/router
jest.mock('next/router', () => ({
    useRouter: () => ({
        route: '/',
        pathname: '/',
        query: {},
        asPath: '/',
        push: jest.fn(),
        replace: jest.fn(),
        reload: jest.fn(),
        back: jest.fn(),
        prefetch: jest.fn().mockResolvedValue(undefined),
        beforePopState: jest.fn(),
        events: {
            on: jest.fn(),
            off: jest.fn(),
            emit: jest.fn(),
        },
    }),
}));

// Mock Clerk authentication
jest.mock('@clerk/nextjs', () => ({
    useUser: () => ({
        user: { id: 'test_user_id', firstName: 'Test', lastName: 'User' },
        isLoaded: true,
        isSignedIn: true,
    }),
    useAuth: () => ({
        userId: 'test_user_id',
        getToken: () => Promise.resolve('mock_token'),
        isLoaded: true,
        isSignedIn: true,
    }),
    ClerkProvider: ({ children }) => children,
    SignedIn: ({ children }) => children,
    SignedOut: () => null,
}));

// Mock matchMedia for ThemeProvider
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(), // deprecated
        removeListener: jest.fn(), // deprecated
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
    })),
});

const { server } = require('./src/mocks/server');

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
