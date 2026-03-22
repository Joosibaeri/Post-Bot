const nextJest = require('next/jest');

const createJestConfig = nextJest({
    // Provide the path to your Next.js app to load next.config.js and .env files
    dir: './',
});

// Add any custom config to be passed to Jest
const customJestConfig = {
    // Add more setup options before each test is run
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

    // Use jsdom for testing React components
    testEnvironment: 'jest-environment-jsdom',
    testEnvironmentOptions: {
        customExportConditions: [''],
    },

    // Module path aliases (match tsconfig paths)
    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
    },

    // Test file patterns
    testMatch: [
        '<rootDir>/__tests__/**/*.test.{ts,tsx}',
        '<rootDir>/src/**/*.test.{ts,tsx}',
    ],

    // Ignore patterns
    testPathIgnorePatterns: [
        '<rootDir>/node_modules/',
        '<rootDir>/.next/',
    ],

    // Transform these ESM dependencies inside node_modules
    transformIgnorePatterns: [
        '/node_modules/(?!(msw|@mswjs|until-async|is-node-process)/)',
    ],

    // Coverage configuration
    collectCoverageFrom: [
        'src/**/*.{ts,tsx}',
        '!src/**/*.d.ts',
        '!src/**/_*.{ts,tsx}',
    ],
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = async () => {
    const nextJestConfig = await createJestConfig(customJestConfig)();
    
    // next/jest ignores transformIgnorePatterns in customJestConfig, so we manually override them here
    nextJestConfig.transformIgnorePatterns = [
        ...customJestConfig.transformIgnorePatterns,
        ...nextJestConfig.transformIgnorePatterns.filter(pattern => pattern !== '/node_modules/')
    ];
    
    return nextJestConfig;
};
