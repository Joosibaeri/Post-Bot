import Head from 'next/head';
import { useRouter } from 'next/router';

interface SEOHeadProps {
  title?: string;
  description?: string;
  keywords?: string;
  ogImage?: string;
  ogUrl?: string;
  canonicalUrl?: string;
}

const DEFAULT_SITE_URL = 'https://linkedin-post-bot.com';

function toAbsoluteUrl(url: string, baseUrl: string): string {
  if (/^https?:\/\//i.test(url)) return url;
  const normalizedPath = url.startsWith('/') ? url : `/${url}`;
  return new URL(normalizedPath, baseUrl).toString();
}

export default function SEOHead({
  title = 'Post Bot - AI-Powered Content Creation',
  description = 'Transform your development activity into engaging social media posts automatically. AI-powered content generation with Groq LLM, activity tracking, and automated posting.',
  keywords = 'LinkedIn, automation, AI, content creation, social media, GitHub, posts, marketing, Groq, LLM',
  ogImage = '/og-image.png',
  ogUrl,
  canonicalUrl
}: SEOHeadProps) {
  const router = useRouter();
  const siteUrl = (process.env.NEXT_PUBLIC_SITE_URL || DEFAULT_SITE_URL).replace(/\/$/, '');
  const currentPath = (router.asPath || '/').split('?')[0].split('#')[0] || '/';
  const resolvedCanonicalUrl = toAbsoluteUrl(canonicalUrl || currentPath, siteUrl);
  const resolvedOgUrl = toAbsoluteUrl(ogUrl || resolvedCanonicalUrl, siteUrl);
  const resolvedOgImage = toAbsoluteUrl(ogImage, siteUrl);

  // Structured data for SEO
  const structuredData = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Post Bot',
    description: description,
    url: resolvedCanonicalUrl,
    image: resolvedOgImage,
    applicationCategory: 'SocialNetworkingApplication',
    operatingSystem: 'Web',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD'
    }
  };

  return (
    <Head>
      {/* Basic Meta Tags */}
      <title key="title">{title}</title>
      <meta key="description" name="description" content={description} />
      <meta key="keywords" name="keywords" content={keywords} />
      <meta key="author" name="author" content="Post Bot" />
      <meta key="viewport" name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0" />
      <meta key="charset" charSet="UTF-8" />

      {/* Canonical URL */}
      <link key="canonical" rel="canonical" href={resolvedCanonicalUrl} />

      {/* Open Graph / Facebook */}
      <meta key="og:type" property="og:type" content="website" />
      <meta key="og:url" property="og:url" content={resolvedOgUrl} />
      <meta key="og:title" property="og:title" content={title} />
      <meta key="og:description" property="og:description" content={description} />
      <meta key="og:image" property="og:image" content={resolvedOgImage} />
      <meta key="og:site_name" property="og:site_name" content="Post Bot" />
      <meta key="og:locale" property="og:locale" content="en_US" />

      {/* Twitter Card */}
      <meta key="twitter:card" name="twitter:card" content="summary_large_image" />
      <meta key="twitter:url" name="twitter:url" content={resolvedOgUrl} />
      <meta key="twitter:title" name="twitter:title" content={title} />
      <meta key="twitter:description" name="twitter:description" content={description} />
      <meta key="twitter:image" name="twitter:image" content={resolvedOgImage} />

      {/* Additional Meta Tags */}
      <meta name="robots" content="index, follow, max-image-preview:large" />
      <meta name="language" content="English" />
      <meta name="revisit-after" content="7 days" />

      {/* Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />

      {/* Preconnect to external domains */}
      <link key="preconnect-unsplash" rel="preconnect" href="https://images.unsplash.com" />
      <link key="dns-prefetch-unsplash" rel="dns-prefetch" href="https://images.unsplash.com" />
    </Head>
  );
}

