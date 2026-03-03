const steps = [
    {
        step: '01',
        title: 'Connect Your GitHub',
        desc: "Link your GitHub account and we'll automatically scan your recent commits, PRs, and repository updates.",
        icon: '🔗'
    },
    {
        step: '02',
        title: 'AI Generates Posts',
        desc: 'Our AI analyzes your activity and crafts engaging LinkedIn posts that showcase your work professionally.',
        icon: '✨'
    },
    {
        step: '03',
        title: 'Review & Publish',
        desc: 'Edit if needed, add images, and publish directly to LinkedIn with one click. Build your brand effortlessly.',
        icon: '🚀'
    }
];

export default function HowItWorksSection() {
    return (
        <div id="how-it-works" className="max-w-7xl mx-auto py-24 border-t border-gray-200 dark:border-white/10">
            <div className="text-center mb-16">
                <span className="inline-block px-4 py-1 rounded-full bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-300 text-sm font-medium mb-4">
                    Simple 3-Step Process
                </span>
                <h2 className="text-3xl md:text-5xl font-bold mb-4">How It Works</h2>
                <p className="text-xl text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
                    From code to content in minutes, not hours.
                </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 relative">
                {/* Connector line (desktop only) */}
                <div className="hidden md:block absolute top-16 left-1/6 right-1/6 h-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"></div>

                {steps.map((item, i) => (
                    <div key={i} className="relative text-center group">
                        <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-purple-500/25 group-hover:scale-110 transition-transform z-10 relative">
                            {item.step}
                        </div>
                        <div className="text-4xl mb-4">{item.icon}</div>
                        <h3 className="text-xl font-bold mb-3">{item.title}</h3>
                        <p className="text-gray-500 dark:text-gray-400 leading-relaxed max-w-sm mx-auto">{item.desc}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
