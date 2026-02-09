import { Html, Head, Main, NextScript } from 'next/document';

/**
 * Custom _document.tsx
 *
 * The inline script runs *before* React hydrates, reading the stored
 * theme from localStorage and applying the `dark` / `light` class on
 * <html>. This eliminates the "flash of wrong theme" (FOWT) that
 * occurs when the ThemeProvider sets the class inside useEffect.
 */
export default function Document() {
  return (
    <Html lang="en" suppressHydrationWarning>
      <Head />
      <body>
        {/* Blocking script — runs before first paint */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('theme');
                  if (theme === 'light' || theme === 'dark') {
                    document.documentElement.classList.add(theme);
                  } else {
                    document.documentElement.classList.add('dark');
                  }
                } catch(e) {
                  document.documentElement.classList.add('dark');
                }
              })();
            `,
          }}
        />
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
