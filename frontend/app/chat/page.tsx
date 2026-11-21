"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Send,
  Sparkles,
  Quote,
  FileText,
  X,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Plus,
  BookOpen,
  Calendar,
  Building2,
  Briefcase,
  Bell,
  Clock,
  CheckCircle2,
  Info,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import {
  ChatMessage,
  CitationItem,
  SUGGESTED_QUESTION_CATEGORIES,
  MOCK_INITIAL_MESSAGES,
  MOCK_CITATIONS,
} from "@/lib/mockData";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(MOCK_INITIAL_MESSAGES["conv-101"] || []);
  const [inputValue, setInputValue] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [activeCategory, setActiveCategory] = useState("cat-exams");
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamedText]);

  const handleSendMessage = (textToSend?: string) => {
    const question = (textToSend || inputValue).trim();
    if (!question || isStreaming) return;

    setInputValue("");
    setShowSuggestions(false);

    // 1. Append user message
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: question,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setStreamedText("");

    // Simulate RAG generation with token streaming
    setTimeout(() => {
      let answerText = "";
      let matchedCitations: CitationItem[] = [];

      if (question.toLowerCase().includes("cgpa") || question.toLowerCase().includes("passing")) {
        answerText =
          "According to Section 7.1 of the University Academic Regulations [Source 1], undergraduate students must maintain a minimum Cumulative Grade Point Average (CGPA) of 6.0 on a 10.0 scale with no active backlogs to be awarded a Bachelor of Technology degree.";
        matchedCitations = [MOCK_CITATIONS[1]];
      } else if (question.toLowerCase().includes("attendance") || question.toLowerCase().includes("medical")) {
        answerText =
          "In accordance with Section 4.2 of the Academic Regulations [Source 1], all students are strictly required to maintain a minimum of 75% physical attendance across all registered courses. Shortages between 65% and 74% may be condoned solely on valid medical grounds.";
        matchedCitations = [MOCK_CITATIONS[0]];
      } else if (question.toLowerCase().includes("hostel") || question.toLowerCase().includes("curfew") || question.toLowerCase().includes("night")) {
        answerText =
          "As detailed in the Hostel Conduct Rules [Source 1], campus gate entry for hostel residents closes at 21:30 hrs. Night-out passes must be submitted digitally via the student portal with prior verified guardian consent.";
        matchedCitations = [MOCK_CITATIONS[3]];
      } else if (question.toLowerCase().includes("re-eval") || question.toLowerCase().includes("backlog")) {
        answerText =
          "Per the Examination Ordinance [Source 1], students may submit an application for answer book re-evaluation within 14 calendar days from result notification along with a fee of Rs. 500 per theoretical paper.";
        matchedCitations = [MOCK_CITATIONS[2]];
      } else {
        answerText =
          "Based on the available university documents [Source 1], the policy details provisions applicable to all registered students under regular academic session guidelines.";
        matchedCitations = [MOCK_CITATIONS[0]];
      }

      // Stream tokens with typewriter effect
      const words = answerText.split(" ");
      let currentIdx = 0;

      const interval = setInterval(() => {
        if (currentIdx < words.length) {
          const chunk = words[currentIdx] + " ";
          setStreamedText((prev) => prev + chunk);
          currentIdx++;
        } else {
          clearInterval(interval);
          setIsStreaming(false);
          const assistantMsg: ChatMessage = {
            id: `msg-${Date.now() + 1}`,
            role: "assistant",
            content: answerText,
            createdAt: new Date().toISOString(),
            citations: matchedCitations,
          };
          setMessages((prev) => [...prev, assistantMsg]);
          setStreamedText("");
        }
      }, 35);
    }, 400);
  };

  const handleNewChat = () => {
    setMessages([]);
    setShowSuggestions(true);
    setSelectedCitation(null);
  };

  const categoryIcons: Record<string, React.ReactNode> = {
    "cat-exams": <BookOpen className="w-3.5 h-3.5" />,
    "cat-attendance": <Clock className="w-3.5 h-3.5" />,
    "cat-calendar": <Calendar className="w-3.5 h-3.5" />,
    "cat-hostel": <Building2 className="w-3.5 h-3.5" />,
    "cat-placement": <Briefcase className="w-3.5 h-3.5" />,
    "cat-notices": <Bell className="w-3.5 h-3.5" />,
  };

  return (
    <AppShell>
      <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
        {/* Main Chat Flow Area (W-04) */}
        <div className="flex-1 flex flex-col h-full bg-white dark:bg-zinc-950 relative">
          {/* Chat Header Bar */}
          <div className="h-12 border-b border-zinc-200 dark:border-zinc-800 px-6 flex items-center justify-between shrink-0 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                Grounded Assistant (LLaMA 3.1 8B Instant)
              </span>
              <span className="text-[10px] text-zinc-400 font-mono">low-temp 0.1</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSuggestions(!showSuggestions)}
                className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 font-medium px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 cursor-pointer"
              >
                {showSuggestions ? "Hide Suggestions" : "Show Suggestions (W-16)"}
              </button>
              <button
                onClick={handleNewChat}
                className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 transition cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                New Thread
              </button>
            </div>
          </div>

          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
            {messages.length === 0 && (
              <div className="max-w-2xl mx-auto my-8 text-center space-y-2">
                <div className="w-10 h-10 rounded-xl bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center text-accent mx-auto mb-3 shadow-xs">
                  <Sparkles className="w-5 h-5" />
                </div>
                <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
                  How can I help you today?
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-md mx-auto">
                  Ask questions about academic policies, hostel timings, attendance condonation, exams, and degree ordinances.
                </p>
              </div>
            )}

            {/* W-16 Suggested Questions Section */}
            {showSuggestions && (
              <div className="max-w-3xl mx-auto my-4 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-900/40">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-accent" />
                    Suggested Questions (W-16)
                  </span>
                  <button
                    onClick={() => setShowSuggestions(false)}
                    className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-xs cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Category Pills */}
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {SUGGESTED_QUESTION_CATEGORIES.map((cat) => (
                    <button
                      key={cat.id}
                      onClick={() => setActiveCategory(cat.id)}
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition cursor-pointer ${
                        activeCategory === cat.id
                          ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900"
                          : "bg-white dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-700"
                      }`}
                    >
                      {categoryIcons[cat.id]}
                      {cat.name}
                    </button>
                  ))}
                </div>

                {/* Clickable Suggested Questions */}
                <div className="grid grid-cols-1 gap-2">
                  {SUGGESTED_QUESTION_CATEGORIES.find((c) => c.id === activeCategory)?.questions.map(
                    (q, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendMessage(q)}
                        className="text-left text-xs p-2.5 rounded-lg bg-white dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700/80 hover:border-accent dark:hover:border-accent text-zinc-700 dark:text-zinc-300 transition flex items-center justify-between group cursor-pointer"
                      >
                        <span>{q}</span>
                        <Send className="w-3 h-3 text-zinc-400 group-hover:text-accent group-hover:translate-x-0.5 transition shrink-0 ml-2" />
                      </button>
                    )
                  )}
                </div>
              </div>
            )}

            {/* Conversation Messages */}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
              >
                <div className="text-[10px] text-zinc-400 mb-1 px-1">
                  {msg.role === "user" ? "You" : "Knowledge Assistant"}
                </div>
                <div
                  className={`max-w-2xl rounded-xl px-4 py-3 text-xs leading-relaxed ${
                    msg.role === "user"
                      ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                      : "bg-zinc-100 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800 shadow-2xs whitespace-pre-line"
                  }`}
                >
                  {msg.content}
                </div>

                {/* W-05 Citations Badges */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 mt-2 pl-1">
                    <span className="text-[10px] font-semibold text-zinc-400 flex items-center gap-1">
                      <Quote className="w-3 h-3 text-accent" /> Sources:
                    </span>
                    {msg.citations.map((cit, cIdx) => (
                      <button
                        key={cit.id || cIdx}
                        onClick={() => setSelectedCitation(cit)}
                        className={`text-[11px] px-2.5 py-1 rounded-md border font-medium transition flex items-center gap-1.5 cursor-pointer ${
                          selectedCitation?.id === cit.id
                            ? "bg-accent text-white border-accent shadow-xs"
                            : "bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 border-zinc-200 dark:border-zinc-800 hover:border-accent"
                        }`}
                      >
                        <FileText className="w-3 h-3" />
                        <span>
                          {cit.document} · Page {cit.page}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {/* Streaming Message Indicator */}
            {isStreaming && (
              <div className="flex flex-col items-start">
                <div className="text-[10px] text-zinc-400 mb-1 px-1">
                  Knowledge Assistant (Streaming SSE...)
                </div>
                <div className="max-w-2xl rounded-xl px-4 py-3 text-xs leading-relaxed bg-zinc-100 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800 shadow-2xs whitespace-pre-line">
                  {streamedText}
                  <span className="inline-block w-1.5 h-3 ml-0.5 bg-accent animate-pulse" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Prompt Input Box */}
          <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-white/95 dark:bg-zinc-950/95">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="max-w-3xl mx-auto flex items-center gap-2"
            >
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask about grading formulas, attendance policies, re-evaluation, hostel rules..."
                className="flex-1 py-2.5 px-4 text-xs rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-accent focus:border-accent"
                disabled={isStreaming}
              />
              <button
                type="submit"
                disabled={!inputValue.trim() || isStreaming}
                className="p-2.5 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition disabled:opacity-40 cursor-pointer"
                aria-label="Send Message"
              >
                {isStreaming ? (
                  <RefreshCw className="w-4 h-4 animate-spin text-accent" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
            <p className="text-[10px] text-zinc-400 text-center mt-2">
              Responses are grounded strictly in uploaded institutional circulars and ordinances with exact citations.
            </p>
          </div>
        </div>

        {/* W-05 AI Answer + Citation Panel (Slide-Over / Inspector) */}
        {selectedCitation && (
          <aside className="w-80 sm:w-96 border-l border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 flex flex-col h-full shrink-0 animate-in slide-in-from-right duration-200">
            <div className="h-12 border-b border-zinc-200 dark:border-zinc-800 px-4 flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                <Quote className="w-3.5 h-3.5 text-accent" />
                Citation Inspector (W-05)
              </span>
              <button
                onClick={() => setSelectedCitation(null)}
                className="p-1 rounded text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Document Meta Card */}
              <div className="p-3.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-2xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-accent">
                    Verified Source
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 font-semibold">
                    Score: {Math.round(selectedCitation.relevanceScore * 100)}%
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                  {selectedCitation.document}
                </h4>
                <div className="flex items-center gap-3 text-[11px] text-zinc-500 dark:text-zinc-400">
                  <span>Page {selectedCitation.page}</span>
                  {selectedCitation.section && <span>• {selectedCitation.section}</span>}
                </div>
              </div>

              {/* Verified Text Chunk Snippet */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
                  Extracted Excerpt
                </label>
                <div className="p-3 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed italic">
                  &ldquo;{selectedCitation.snippet}&rdquo;
                </div>
              </div>

              {/* Actions */}
              <div className="pt-2">
                <Link
                  href="/documents"
                  className="w-full py-2 px-3 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-xs font-medium text-zinc-800 dark:text-zinc-200 transition flex items-center justify-center gap-1.5"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Open in Document Preview (W-08)
                </Link>
              </div>
            </div>
          </aside>
        )}
      </div>
    </AppShell>
  );
}
