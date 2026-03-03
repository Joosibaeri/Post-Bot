import Link from 'next/link';

const features = [
    { title: 'Multi-AI Generation', desc: 'Choose from 4 AI providers — Groq, OpenAI, Anthropic, or Mistral — to craft posts in your unique voice.', icon: '🤖' },
    { title: 'Smart Scheduling', desc: "Schedule posts for optimal times. Celery-powered queue ensures reliable delivery even when you're offline.", icon: '📅' },
    { title: 'Persona Engine', desc: 'Build a writing persona from your style, tone, and topics. Every post sounds authentically you.', icon: '🧠' },
    { title: 'Code to Content', desc: 'Automatically turn your Git commits, PRs, and releases into engaging LinkedIn stories.', icon: '⚡' },
    { title: 'One-Click Publish', desc: 'Review AI-generated drafts, edit if needed, and publish directly to LinkedIn via OAuth.', icon: '🚀' },
    { title: 'Stripe Payments', desc: 'Upgrade to Pro for unlimited posts, premium AI models, and advanced scheduling.', icon: '💳' }
];

export default function FeaturesSection() {
    return (
        <div id="features" className="max-w-7xl mx-auto py-24">
            <div className="text-center mb-16">
                <h2 className="text-3xl md:text-5xl font-bold mb-4">Everything you need to grow</h2>
                <p className="text-xl text-gray-500 dark:text-gray-400">Automate your personal brand while you code.</p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
                {features.map((feature, i) => (
                    <div key={i} className="group p-8 rounded-2xl bg-white dark:bg-white/5 border border-gray-100 dark:border-white/10 hover:border-blue-500/50 transition-all duration-300 hover:shadow-2xl hover:shadow-blue-500/10">
                        <div className="w-14 h-14 bg-blue-50 dark:bg-blue-900/20 rounded-xl flex items-center justify-center text-3xl mb-6 group-hover:scale-110 transition-transform">
                            {feature.icon}
                        </div>
                        <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
                        <p className="text-gray-500 dark:text-gray-400 leading-relaxed">{feature.desc}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
