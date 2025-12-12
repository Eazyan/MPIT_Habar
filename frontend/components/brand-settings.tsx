"use client";

import { useState, useEffect } from "react";
import { GlassCard } from "@/components/ui/glass-card";
import { X, Save } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface BrandSettingsProps {
    isOpen: boolean;
    onClose: () => void;
}

export function BrandSettings({ isOpen, onClose }: BrandSettingsProps) {
    const [profile, setProfile] = useState({
        name: "",
        description: "",
        tone_of_voice: "",
        target_audience: "",
        keywords: "",
        examples: ""
    });

    useEffect(() => {
        const saved = localStorage.getItem("brandProfile");
        if (saved) {
            const parsed = JSON.parse(saved);
            setProfile({
                ...parsed,
                keywords: parsed.keywords.join(", "),
                examples: parsed.examples.join("\n---\n")
            });
        }
    }, [isOpen]);

    const handleSave = () => {
        const formatted = {
            ...profile,
            keywords: profile.keywords.split(",").map(k => k.trim()).filter(k => k),
            examples: profile.examples.split("\n---\n").map(e => e.trim()).filter(e => e)
        };
        localStorage.setItem("brandProfile", JSON.stringify(formatted));
        onClose();
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="w-full max-w-lg"
                    >
                        <GlassCard className="relative max-h-[90vh] overflow-y-auto">
                            <button
                                onClick={onClose}
                                className="absolute top-4 right-4 text-gray-400 hover:text-white"
                            >
                                <X className="w-5 h-5" />
                            </button>

                            <h2 className="text-xl font-bold text-white mb-6">Настройки Бренда</h2>

                            <div className="space-y-4">
                                <div>
                                    <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">Название Бренда</label>
                                    <input
                                        type="text"
                                        value={profile.name}
                                        onChange={e => setProfile({ ...profile, name: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500"
                                        placeholder="Apple, Tesla, Ромашка..."
                                    />
                                </div>

                                <div>
                                    <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">Описание деятельности</label>
                                    <textarea
                                        value={profile.description}
                                        onChange={e => setProfile({ ...profile, description: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500 h-24 resize-none"
                                        placeholder="Мы делаем лучшие смартфоны..."
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">Tone of Voice</label>
                                        <input
                                            type="text"
                                            value={profile.tone_of_voice}
                                            onChange={e => setProfile({ ...profile, tone_of_voice: e.target.value })}
                                            className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500"
                                            placeholder="Дерзкий, Дружелюбный..."
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">Целевая аудитория</label>
                                        <input
                                            type="text"
                                            value={profile.target_audience}
                                            onChange={e => setProfile({ ...profile, target_audience: e.target.value })}
                                            className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500"
                                            placeholder="IT-специалисты, 25-35..."
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">Ключевые слова (через запятую)</label>
                                    <input
                                        type="text"
                                        value={profile.keywords}
                                        onChange={e => setProfile({ ...profile, keywords: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500"
                                        placeholder="iPhone, iOS, Mac..."
                                    />
                                </div>

                                <div>
                                    <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">Примеры постов (разделитель ---)</label>
                                    <textarea
                                        value={profile.examples}
                                        onChange={e => setProfile({ ...profile, examples: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500 h-32 resize-none"
                                        placeholder="Пример 1... --- Пример 2..."
                                    />
                                </div>

                                <button
                                    onClick={handleSave}
                                    className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2 mt-4"
                                >
                                    <Save className="w-5 h-5" />
                                    Сохранить Профиль
                                </button>
                            </div>
                        </GlassCard>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
