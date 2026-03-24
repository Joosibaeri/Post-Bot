const faqs = [
    {
        q: 'Is PostBot really free?',
        a: 'Yes! Our Free tier gives you 10 posts per month, Groq AI generation, persona engine, and post scheduling. No credit card required. Pro is not live yet, but you can join the waitlist for launch access.'
    },
    {
        q: 'What AI models power PostBot?',
        a: 'PostBot supports 4 AI providers: Groq (Llama 3.3 70B, free), OpenAI (GPT-4o), Anthropic (Claude 3.5 Sonnet), and Mistral (Mistral Large). Free users get Groq; Pro users can choose any provider.'
    },
    {
        q: 'Is my data secure?',
        a: "Absolutely. We use OAuth 2.0 for LinkedIn (no passwords stored), encrypt all API keys, and never store your GitHub code. We're fully GDPR compliant."
    },
    {
        q: "Does this violate LinkedIn's Terms of Service?",
        a: "No. PostBot uses LinkedIn's official OAuth and Share APIs. All posts are user-initiated (not automated bots). We follow all LinkedIn compliance guidelines."
    },
    {
        q: 'Can I edit the AI-generated posts?',
        a: 'Yes! Every post can be fully edited before publishing. Add your personal touch, adjust tone, include hashtags - you have complete control.'
    },
    {
        q: 'When will Pro launch?',
        a: "We’re finalizing the paid experience and Paystack rollout. Join the waitlist and we’ll let you know as soon as Pro is available."
    }
];

export default function FAQSection() {
    return (
        <div id="faq" className="max-w-4xl mx-auto py-24 border-t border-gray-200 dark:border-white/10">
            <div className="text-center mb-16">
                <span className="inline-block px-4 py-1 rounded-full bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-300 text-sm font-medium mb-4">
                    Got Questions?
                </span>
                <h2 className="text-3xl md:text-5xl font-bold mb-4">Frequently Asked Questions</h2>
                <p className="text-xl text-gray-500 dark:text-gray-400">
                    Everything you need to know about PostBot.
                </p>
            </div>

            <div className="space-y-4">
                {faqs.map((faq, i) => (
                    <details key={i} className="group p-6 rounded-2xl bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 hover:border-blue-500/30 transition-all cursor-pointer">
                        <summary className="flex items-center justify-between font-semibold text-lg list-none">
                            {faq.q}
                            <svg className="w-5 h-5 text-gray-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </summary>
                        <p className="mt-4 text-gray-600 dark:text-gray-400 leading-relaxed">{faq.a}</p>
                    </details>
                ))}
            </div>
        </div>
    );
}
