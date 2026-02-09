import { SignIn } from "@clerk/nextjs";
import Link from "next/link";
import { useEffect, useState } from "react";
import ThemeToggle from "@/components/ThemeToggle";
import dynamic from "next/dynamic";

const InteractiveBackground = dynamic(
    () => import("@/components/ui/InteractiveBackground"),
    { ssr: false, loading: () => null }
);

export default function SignInPage() {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) {
        return null;
    }

    return (
        <div className="min-h-screen flex">
            {/* Animated Background - override opacity for visibility */}
            <InteractiveBackground className="!opacity-30 !z-10" />
            {/* Left Side - Branding */}
            <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 relative overflow-hidden">
                {/* Background Pattern */}
                <div className="absolute inset-0 opacity-10">
                    <div className="absolute top-20 left-20 w-72 h-72 bg-white rounded-full blur-3xl"></div>
                    <div className="absolute bottom-20 right-20 w-96 h-96 bg-white rounded-full blur-3xl"></div>
                </div>

                <div className="relative z-10 flex flex-col justify-center px-12 xl:px-20 text-white">
                    {/* Logo */}
                    <div className="flex items-center gap-3 mb-12">
                        <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                            {/* Lightning bolt - Post Bot logo */}
                            <svg className="w-7 h-7" viewBox="0 0 32 32" fill="none">
                                <path d="M18 4l-8 12h6l-2 12 10-14h-6l4-10z" fill="white" stroke="white" strokeWidth="0.5" />
                            </svg>
                        </div>
                        <span className="text-2xl font-bold">Post Bot</span>
                    </div>

                    {/* Main Heading */}
                    <h1 className="text-4xl xl:text-5xl font-bold mb-6 leading-tight">
                        Turn your code into<br />
                        <span className="text-blue-200">professional content</span>
                    </h1>

                    <p className="text-lg text-blue-100 mb-10 max-w-md">
                        Transform your GitHub activity into engaging LinkedIn posts with AI-powered content generation.
                    </p>

                    {/* Features */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <span className="text-blue-100">Scan GitHub commits, PRs, and pushes</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <span className="text-blue-100">AI generates professional posts</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <span className="text-blue-100">One-click publish to LinkedIn</span>
                        </div>
                    </div>

                    {/* Testimonial/Stats */}
                    <div className="mt-12 pt-8 border-t border-white/20">
                        <div className="flex items-center gap-8">
                            <div>
                                <div className="text-3xl font-bold">10K+</div>
                                <div className="text-sm text-blue-200">Posts Generated</div>
                            </div>
                            <div>
                                <div className="text-3xl font-bold">500+</div>
                                <div className="text-sm text-blue-200">Active Users</div>
                            </div>
                            <div>
                                <div className="text-3xl font-bold">4.9★</div>
                                <div className="text-sm text-blue-200">User Rating</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Side - Sign In Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-8 bg-gradient-to-br from-gray-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800 relative overflow-hidden">
                {/* Decorative Background Elements */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-blue-200/30 dark:bg-blue-800/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
                <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-200/30 dark:bg-purple-800/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

                <div className="w-full max-w-md relative z-10">
                    {/* Mobile Logo */}
                    <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
                            <svg className="w-6 h-6" viewBox="0 0 32 32" fill="none">
                                <path d="M18 4l-8 12h6l-2 12 10-14h-6l4-10z" fill="white" stroke="white" strokeWidth="0.5" />
                            </svg>
                        </div>
                        <span className="text-xl font-bold text-gray-900 dark:text-white">Post Bot</span>
                    </div>

                    {/* Theme Toggle & Back */}
                    <div className="absolute -top-2 right-0 flex items-center gap-2">
                        <Link
                            href="/"
                            className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                            title="Back to home"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1" />
                            </svg>
                        </Link>
                        <ThemeToggle />
                    </div>

                    {/* Header */}
                    <div className="text-center mb-6">
                        <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl shadow-lg shadow-blue-500/25 mb-4">
                            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                            </svg>
                        </div>
                        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
                            Welcome back
                        </h2>
                        <p className="text-gray-500 dark:text-gray-400 text-sm">
                            Sign in to continue managing your LinkedIn content
                        </p>
                    </div>

                    {/* Form Card */}
                    <div className="bg-white/70 dark:bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-200/60 dark:border-gray-700/60 p-6 shadow-xl shadow-gray-200/40 dark:shadow-black/20">
                        {/* Clerk Sign In Component */}
                        <div className="clerk-container">
                            <SignIn
                                path="/sign-in"
                                routing="path"
                                signUpUrl="/sign-up"
                                appearance={{
                                    elements: {
                                        rootBox: "mx-auto w-full",
                                        card: "shadow-none bg-transparent p-0",
                                        headerTitle: "hidden",
                                        headerSubtitle: "hidden",
                                        socialButtonsBlockButton: "bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 transition-all shadow-sm hover:shadow-md",
                                        formButtonPrimary: "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40",
                                        footerActionLink: "text-blue-600 hover:text-blue-700",
                                        formFieldInput: "bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 dark:text-white text-gray-900 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all",
                                        formFieldLabel: "text-gray-700 dark:text-gray-300 font-medium",
                                        identityPreviewEditButton: "text-blue-600",
                                        formResendCodeLink: "text-blue-600",
                                        dividerLine: "bg-gray-200 dark:bg-gray-600",
                                        dividerText: "text-gray-400 dark:text-gray-500",
                                        footer: "hidden",
                                    }
                                }}
                            />
                        </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="mt-6 grid grid-cols-3 gap-3">
                        <div className="text-center p-3 bg-white/50 dark:bg-gray-800/30 rounded-xl border border-gray-200/40 dark:border-gray-700/40">
                            <div className="text-lg font-bold text-gray-900 dark:text-white">4</div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">AI Models</div>
                        </div>
                        <div className="text-center p-3 bg-white/50 dark:bg-gray-800/30 rounded-xl border border-gray-200/40 dark:border-gray-700/40">
                            <div className="text-lg font-bold text-gray-900 dark:text-white">10</div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">Free Posts/Day</div>
                        </div>
                        <div className="text-center p-3 bg-white/50 dark:bg-gray-800/30 rounded-xl border border-gray-200/40 dark:border-gray-700/40">
                            <div className="text-lg font-bold text-gray-900 dark:text-white">1-Click</div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">Publish</div>
                        </div>
                    </div>

                    {/* Footer Link */}
                    <div className="mt-5 text-center text-sm text-gray-500 dark:text-gray-400">
                        Don&apos;t have an account?{' '}
                        <Link href="/sign-up" className="text-blue-600 hover:text-blue-700 font-semibold hover:underline transition-colors">
                            Sign up for free
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
