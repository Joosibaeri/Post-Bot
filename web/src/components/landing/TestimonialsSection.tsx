const testimonials = [
    {
        quote: "PostBot saved me hours every week. My LinkedIn engagement has tripled since I started using it to share my GitHub activity.",
        author: "Sarah Chen",
        role: "Senior Software Engineer",
        company: "Stripe",
        avatar: "👩‍💻"
    },
    {
        quote: "As a maintainer of multiple open source projects, I never had time to post about my work. Now it's automated and I get way more visibility.",
        author: "Marcus Johnson",
        role: "Open Source Maintainer",
        company: "React Native Community",
        avatar: "👨‍💻"
    },
    {
        quote: "I landed my dream job partly because recruiters found my LinkedIn posts about my coding projects. PostBot made that happen.",
        author: "Priya Sharma",
        role: "Full Stack Developer",
        company: "Vercel",
        avatar: "👩‍🔬"
    }
];

export default function TestimonialsSection() {
    return (
        <div id="testimonials" className="max-w-7xl mx-auto py-24 border-t border-gray-200 dark:border-white/10">
            <div className="text-center mb-16">
                <span className="inline-block px-4 py-1 rounded-full bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-300 text-sm font-medium mb-4">
                    Loved by Developers
                </span>
                <h2 className="text-3xl md:text-5xl font-bold mb-4">What Developers Say</h2>
                <p className="text-xl text-gray-500 dark:text-gray-400">
                    Join hundreds of developers building their personal brand.
                </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
                {testimonials.map((testimonial, i) => (
                    <div key={i} className="p-8 rounded-2xl bg-white dark:bg-white/5 border border-gray-100 dark:border-white/10 hover:border-blue-500/30 transition-all duration-300 hover:shadow-xl">
                        {/* Stars */}
                        <div className="flex gap-1 mb-4 text-yellow-400">
                            {[1, 2, 3, 4, 5].map(star => (
                                <svg key={star} className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                </svg>
                            ))}
                        </div>
                        <p className="text-gray-600 dark:text-gray-300 mb-6 leading-relaxed italic">
                            &quot;{testimonial.quote}&quot;
                        </p>
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/50 dark:to-purple-900/50 flex items-center justify-center text-2xl">
                                {testimonial.avatar}
                            </div>
                            <div>
                                <div className="font-semibold text-gray-900 dark:text-white">{testimonial.author}</div>
                                <div className="text-sm text-gray-500 dark:text-gray-400">{testimonial.role} @ {testimonial.company}</div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
