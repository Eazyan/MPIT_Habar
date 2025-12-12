"use client";

import { GlassCard } from "@/components/ui/glass-card";
import { motion } from "framer-motion";
import { ArrowLeft, Share2, Copy, Check, Download, ExternalLink, AlertTriangle, CheckCircle, Eye, Send } from "lucide-react";
import Link from "next/link";
import { useState, useEffect } from "react";

export default function PlanPage({ params }: { params: { id: string } }) {
    const [activeTab, setActiveTab] = useState("telegram");
    const [copied, setCopied] = useState(false);
    const [plan, setPlan] = useState<any>(null);

    useEffect(() => {
        const saved = localStorage.getItem('lastPlan');
        if (saved) {
            setPlan(JSON.parse(saved));
        }
    }, []);

    if (!plan) return <div className="min-h-screen flex items-center justify-center text-white">Загрузка...</div>;

    const activePost = plan.posts.find((p: any) => p.platform === activeTab);

    const handleCopy = () => {
        if (activePost) {
            navigator.clipboard.writeText(activePost.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const getVerdictColor = (verdict: string) => {
        if (verdict?.toLowerCase().includes("игнор")) return "text-gray-400";
        if (verdict?.toLowerCase().includes("отвечать")) return "text-green-400";
        if (verdict?.toLowerCase().includes("монитор")) return "text-yellow-400";
        return "text-blue-400";
    };

    return (
        <main className="min-h-screen p-6 pb-20">
            <div className="max-w-4xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
                        <ArrowLeft className="w-5 h-5" />
                        <span>Назад к Дашборду</span>
                    </Link>
                    <div className="flex gap-2">
                        <button className="p-2 rounded-full bg-white/5 hover:bg-white/10 transition-colors">
                            <Download className="w-5 h-5 text-white" />
                        </button>
                        <button className="p-2 rounded-full bg-white/5 hover:bg-white/10 transition-colors">
                            <Share2 className="w-5 h-5 text-white" />
                        </button>
                    </div>
                </div>

                {/* PR Strategy Section (The "Brain") */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <GlassCard className="col-span-2 bg-gradient-to-br from-blue-900/20 to-purple-900/20 border-blue-500/30">
                        <div className="flex items-start justify-between mb-4">
                            <div>
                                <h2 className="text-sm font-bold text-blue-300 uppercase tracking-wider mb-1">PR Стратегия</h2>
                                <div className={`text-2xl font-bold ${getVerdictColor(plan.analysis.pr_verdict)}`}>
                                    {plan.analysis.pr_verdict || "Анализ..."}
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Relevance Score</div>
                                <div className="text-2xl font-bold text-white">{plan.analysis.relevance_score || 0}/100</div>
                            </div>
                        </div>
                        <p className="text-gray-300 text-sm italic border-l-2 border-white/20 pl-4 my-4">
                            "{plan.analysis.pr_reasoning}"
                        </p>

                        {/* Tips Section */}
                        {plan.analysis.tips && plan.analysis.tips.length > 0 && (
                            <div className="mb-4 bg-white/5 rounded-lg p-3">
                                <h3 className="text-xs font-bold text-blue-300 uppercase mb-2 flex items-center gap-2">
                                    <AlertTriangle className="w-3 h-3" /> Советы эксперта
                                </h3>
                                <ul className="space-y-1">
                                    {plan.analysis.tips.map((tip: string, i: number) => (
                                        <li key={i} className="text-xs text-gray-300 flex items-start gap-2">
                                            <span className="text-blue-500">•</span> {tip}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <div className="flex gap-2 flex-wrap">
                            <span className="text-xs bg-white/10 text-gray-300 px-2 py-1 rounded-md">
                                Sentiment: {plan.analysis.sentiment}
                            </span>
                            {plan.analysis.facts.slice(0, 3).map((fact: string, i: number) => (
                                <span key={i} className="text-xs bg-blue-500/20 text-blue-200 px-2 py-1 rounded-md truncate max-w-[200px]">
                                    {fact}
                                </span>
                            ))}
                        </div>
                    </GlassCard>

                    <GlassCard className="flex flex-col justify-center items-center text-center p-6">
                        <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mb-4">
                            <CheckCircle className="w-8 h-8 text-green-400" />
                        </div>
                        <div className="text-lg font-bold text-white">Готово к публикации</div>
                        <div className="text-sm text-gray-400 mt-2">Контент адаптирован под 7 платформ</div>
                    </GlassCard>
                </div>

                {/* Content Generation Section */}
                <div className="space-y-6">
                    <h3 className="text-xl font-bold text-white">Генерация Контента</h3>

                    {/* Platform Tabs */}
                    <div className="flex overflow-x-auto pb-2 gap-2 no-scrollbar">
                        {plan.posts.map((post: any) => (
                            <button
                                key={post.platform}
                                onClick={() => setActiveTab(post.platform)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${activeTab === post.platform
                                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                                    : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                                    }`}
                            >
                                {post.platform.toUpperCase()}
                            </button>
                        ))}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Text Content */}
                        <GlassCard className="min-h-[400px] relative flex flex-col">
                            <div className="flex-1">
                                <textarea
                                    className="w-full h-full bg-transparent text-gray-100 resize-none focus:outline-none text-sm leading-relaxed min-h-[350px]"
                                    value={activePost?.content || "Нет контента"}
                                    readOnly
                                />
                            </div>
                            <div className="flex justify-end pt-4 border-t border-white/10">
                                <button
                                    onClick={handleCopy}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm font-medium transition-colors"
                                >
                                    {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                    {copied ? "Скопировано" : "Копировать"}
                                </button>
                            </div>
                        </GlassCard>

                        {/* Visual Content */}
                        <div className="space-y-4">
                            <GlassCard className="aspect-square relative overflow-hidden group flex items-center justify-center bg-black/40">
                                {activePost?.image_url ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img
                                        src={activePost.image_url}
                                        alt="Generated visual"
                                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                                    />
                                ) : (
                                    <div className="text-gray-500 flex flex-col items-center">
                                        <Eye className="w-8 h-8 mb-2 opacity-50" />
                                        <span>Нет изображения</span>
                                    </div>
                                )}

                                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-6">
                                    <p className="text-xs text-gray-300 line-clamp-2">
                                        Prompt: {activePost?.image_prompt}
                                    </p>
                                </div>
                            </GlassCard>

                            <button className="w-full bg-green-600 hover:bg-green-500 text-white font-bold py-4 rounded-xl shadow-lg shadow-green-500/20 transition-all flex items-center justify-center gap-2">
                                <Send className="w-5 h-5" />
                                Опубликовать в {activeTab.toUpperCase()}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
