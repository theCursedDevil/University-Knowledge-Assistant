"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
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
  AlertTriangle,
  History,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { LoadingState } from "@/components/SystemStates";
import {
  SUGGESTED_QUESTION_CATEGORIES,
} from "@/lib/mockData";
import {
  fetchConversations,
  createConversation,
  fetchConversationDetail,
  streamChatMessage,
  ApiConversationSummary,
  ApiMessage,
  ApiCitation,
} from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { formatDate } from "@/lib/utils";

export default function ChatPage() {
  const { role, currentUser } = useAuth();

  // Conversations State
  const [conversations, setConversations] = useState<ApiConversationSummary[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ApiMessage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(true);

  // Input & Streaming State
  const [inputValue, setInputValue] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<ApiCitation[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);

  // UI Panels
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [activeCategory, setActiveCategory] = useState("cat-exams");
  const [selectedCitation, setSelectedCitation] = useState<ApiCitation | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  // Load user's conversations on mount or user switch
  const loadConversations = useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const convList = await fetchConversations();
      setConversations(convList);
      if (convList.length > 0) {
        setActiveConvId(convList[0].id);
      } else {
        // Create initial conversation if empty
        const initialConv = await createConversation("New Conversation");
        setConversations([initialConv]);
        setActiveConvId(initialConv.id);
      }
    } catch {
      // Offline fallback
      setConversations([]);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations, currentUser.id]);

  // Load active conversation messages
  const loadActiveMessages = useCallback(async (convId: string) => {
    try {
      const detail = await fetchConversationDetail(convId);
      setMessages(detail.messages || []);
      setShowSuggestions(detail.messages.length === 0);
    } catch {
      setMessages([]);
      setShowSuggestions(true);
    }
  }, []);

  useEffect(() => {
    if (activeConvId) {
      loadActiveMessages(activeConvId);
    }
  }, [activeConvId, loadActiveMessages]);

  // Start a fresh conversation thread
  const handleNewConversation = async () => {
    try {
      const newConv = await createConversation("New Conversation");
      setConversations((prev) => [newConv, ...prev]);
      setActiveConvId(newConv.id);
      setMessages([]);
      setShowSuggestions(true);
      setStreamError(null);
    } catch (err: any) {
      setStreamError(err.message || "Failed to create new conversation.");
    }
  };

  // Submit Question & Consume Server-Sent Events (SSE) Stream
  const handleSendMessage = async (textToSend?: string) => {
    const question = (textToSend || inputValue).trim();
    if (!question || isStreaming) return;

    setInputValue("");
    setShowSuggestions(false);
    setStreamError(null);

    let convId = activeConvId;
    if (!convId) {
      try {
        const newConv = await createConversation("New Conversation");
        setConversations((prev) => [newConv, ...prev]);
        convId = newConv.id;
        setActiveConvId(newConv.id);
      } catch (err: any) {
        setStreamError("Failed to initiate conversation thread.");
        return;
      }
    }

    // Optimistically append user message
    const optimisticUserMsg: ApiMessage = {
      id: `usr-${Date.now()}`,
      conversation_id: convId,
      role: "user",
      content: question,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUserMsg]);

    setIsStreaming(true);
    setStreamingText("");
    setStreamingCitations([]);

    await streamChatMessage({
      conversationId: convId,
      message: question,
      onToken: (token: string) => {
        setStreamingText((prev) => prev + token);
      },
      onCitations: (citations: ApiCitation[]) => {
        setStreamingCitations(citations);
      },
      onComplete: ({ answer, citations, messageId }) => {
        const assistantMsg: ApiMessage = {
          id: messageId || `asst-${Date.now()}`,
          conversation_id: convId!,
          role: "assistant",
          content: answer,
          citations_json: citations,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setIsStreaming(false);
        setStreamingText("");
        setStreamingCitations([]);

        // Refresh conversation listing to update titles/timestamps
        fetchConversations().then(setConversations).catch(() => {});
      },
      onError: (err: Error) => {
        setIsStreaming(false);
        setStreamError(err.message || "Failed to receive response from knowledge engine.");
      },
    });
  };

  return (
    <AppShell>
      <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
        {/* Main Chat Flow Area */}
        <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-zinc-950">
          {/* Conversation Header & Switcher */}
          <div className="p-3.5 px-6 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between gap-4 shrink-0 bg-zinc-50/50 dark:bg-zinc-900/50">
            <div className="flex items-center gap-2 overflow-hidden">
              <Sparkles className="w-4 h-4 text-accent shrink-0" />
              <div className="truncate">
                <span className="font-semibold text-xs text-zinc-900 dark:text-zinc-100 truncate block">
                  {conversations.find((c) => c.id === activeConvId)?.title || "University Knowledge Assistant"}
                </span>
                <span className="text-[11px] text-zinc-400 block truncate">
                  Grounded in official notices, regulations, and handbooks via Qdrant & Groq
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {conversations.length > 1 && (
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs">
                  <History className="w-3.5 h-3.5 text-zinc-400" />
                  <select
                    value={activeConvId || ""}
                    onChange={(e) => setActiveConvId(e.target.value)}
                    className="bg-transparent text-xs text-zinc-700 dark:text-zinc-300 focus:outline-hidden cursor-pointer max-w-[140px] truncate"
                  >
                    {conversations.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.title}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <button
                onClick={handleNewConversation}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 transition cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New</span>
              </button>
            </div>
          </div>

          {/* Messages Stream Container */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
            {isLoadingHistory ? (
              <LoadingState message="Loading conversation history..." />
            ) : messages.length === 0 && !isStreaming ? (
              /* W-16 Suggested Questions Section (Empty Thread State) */
              <div className="max-w-2xl mx-auto py-6 space-y-6">
                <div className="text-center space-y-2">
                  <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-accent/10 text-accent mb-1">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
                    How can I assist your university queries today?
                  </h2>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-md mx-auto">
                    Ask natural-language questions about curriculum, exams, fee payments, hostel curfews, or placement criteria.
                  </p>
                </div>

                {showSuggestions && (
                  <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 p-4 space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-zinc-200 dark:border-zinc-800">
                      <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                        Suggested Topic Explorations
                      </span>
                      <button
                        onClick={() => setShowSuggestions(false)}
                        className="text-[11px] text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
                      >
                        Hide
                      </button>
                    </div>

                    {/* Category Tabs */}
                    <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                      {SUGGESTED_QUESTION_CATEGORIES.map((cat) => (
                        <button
                          key={cat.id}
                          onClick={() => setActiveCategory(cat.id)}
                          className={`px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap transition cursor-pointer ${
                            activeCategory === cat.id
                              ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-semibold"
                              : "bg-white dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100"
                          }`}
                        >
                          {cat.name}
                        </button>
                      ))}
                    </div>

                    {/* Category Questions Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                      {SUGGESTED_QUESTION_CATEGORIES.find((c) => c.id === activeCategory)?.questions.map((q, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendMessage(q)}
                          className="text-left p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:border-accent hover:bg-accent/5 transition text-xs text-zinc-700 dark:text-zinc-300 shadow-2xs group cursor-pointer"
                        >
                          <span className="group-hover:text-accent font-medium leading-relaxed block">{q}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}

            {/* Conversation Turns */}
            {messages.map((msg) => {
              const isUser = msg.role === "user";
              const citations: ApiCitation[] = msg.citations_json || [];

              return (
                <div
                  key={msg.id}
                  className={`flex gap-3 max-w-3xl ${isUser ? "ml-auto justify-end" : "mr-auto justify-start"}`}
                >
                  {!isUser && (
                    <div className="w-7 h-7 rounded-md bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0 mt-0.5">
                      <Sparkles className="w-3.5 h-3.5 text-accent" />
                    </div>
                  )}

                  <div className={`space-y-2 max-w-[85%] ${isUser ? "text-right" : "text-left"}`}>
                    <div
                      className={`inline-block p-3.5 rounded-xl text-xs leading-relaxed text-left ${
                        isUser
                          ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-tr-xs"
                          : "bg-zinc-100/80 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-tl-xs shadow-2xs"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content || "I couldn't find sufficient information about this in the available university documents."}</p>
                    </div>

                    {/* Verified Citations Panel Trigger (W-05) */}
                    {!isUser && citations.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[11px] font-semibold text-zinc-400 inline-flex items-center gap-1">
                          <Quote className="w-3 h-3 text-accent" />
                          Verified Sources:
                        </span>
                        {citations.map((c, i) => (
                          <button
                            key={i}
                            onClick={() => setSelectedCitation(c)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-200/60 dark:bg-zinc-800 hover:bg-accent/15 hover:text-accent border border-zinc-300/50 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 transition cursor-pointer"
                          >
                            <FileText className="w-3 h-3 text-zinc-400" />
                            <span>{c.document}</span>
                            {c.page && <span className="text-zinc-400 font-mono">p.{c.page}</span>}
                          </button>
                        ))}
                      </div>
                    )}

                    <div className="text-[10px] text-zinc-400 font-mono px-1">
                      {formatDate(msg.created_at)}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Live SSE Streaming Bubble */}
            {isStreaming && (
              <div className="flex gap-3 max-w-3xl mr-auto justify-start animate-in fade-in duration-150">
                <div className="w-7 h-7 rounded-md bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0 mt-0.5">
                  <Sparkles className="w-3.5 h-3.5 text-accent animate-pulse" />
                </div>
                <div className="space-y-2 max-w-[85%] text-left">
                  <div className="inline-block p-3.5 rounded-xl text-xs leading-relaxed bg-zinc-100/80 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-tl-xs shadow-2xs">
                    <p className="whitespace-pre-wrap">{streamingText || "Retrieving relevant documents..."}</p>
                    <span className="inline-block w-1.5 h-3.5 ml-1 bg-accent animate-pulse align-middle" />
                  </div>

                  {streamingCitations.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-[11px] font-semibold text-zinc-400 inline-flex items-center gap-1">
                        <Quote className="w-3 h-3 text-accent" />
                        Resolving Sources:
                      </span>
                      {streamingCitations.map((c, i) => (
                        <span
                          key={i}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-200/60 dark:bg-zinc-800 border border-zinc-300/50 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300"
                        >
                          <FileText className="w-3 h-3 text-zinc-400" />
                          <span>{c.document}</span>
                          {c.page && <span className="text-zinc-400 font-mono">p.{c.page}</span>}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error Notification */}
            {streamError && (
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-400 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{streamError}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Chat Input Form */}
          <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="max-w-3xl mx-auto relative flex items-center"
            >
              <input
                type="text"
                placeholder="Ask a question about university notices, regulations, or handbooks..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isStreaming}
                className="w-full pl-4 pr-12 py-3 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-hidden focus:border-accent disabled:opacity-50 transition shadow-2xs"
              />
              <button
                type="submit"
                disabled={!inputValue.trim() || isStreaming}
                className="absolute right-2 p-2 rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 disabled:opacity-40 transition cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
            <div className="max-w-3xl mx-auto mt-2 flex items-center justify-between text-[11px] text-zinc-400 px-1">
              <span>Answers are strictly grounded in university documents with zero hallucination.</span>
              <button
                type="button"
                onClick={() => setShowSuggestions((prev) => !prev)}
                className="hover:text-zinc-600 dark:hover:text-zinc-200 underline cursor-pointer"
              >
                {showSuggestions ? "Hide suggestions" : "Show suggestions"}
              </button>
            </div>
          </div>
        </div>

        {/* W-05 Citation Inspector Slide-over Drawer */}
        {selectedCitation && (
          <div className="w-80 md:w-96 border-l border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 flex flex-col justify-between shrink-0 shadow-lg animate-in slide-in-from-right duration-200 z-30">
            <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Quote className="w-4 h-4 text-accent" />
                <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">Citation Provenance</h3>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 flex-1 overflow-y-auto space-y-4 text-xs">
              <div className="p-3 rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 space-y-2">
                <div className="flex items-center gap-1.5 text-zinc-500 font-semibold uppercase text-[10px]">
                  <FileText className="w-3 h-3 text-accent" />
                  Source Document
                </div>
                <div className="font-bold text-zinc-900 dark:text-zinc-100 text-sm">
                  {selectedCitation.document}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                  <span className="text-[10px] text-zinc-400 block uppercase font-semibold">Page Number</span>
                  <span className="font-mono text-xs text-zinc-800 dark:text-zinc-200 font-bold">
                    {selectedCitation.page ? `Page ${selectedCitation.page}` : "General"}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                  <span className="text-[10px] text-zinc-400 block uppercase font-semibold">Section</span>
                  <span className="text-xs text-zinc-800 dark:text-zinc-200 font-medium truncate block">
                    {selectedCitation.section || "Body"}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-[11px] text-emerald-800 dark:text-emerald-300 space-y-1">
                <div className="flex items-center gap-1.5 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Deterministic Grounding
                </div>
                <p>
                  This citation was resolved directly from vector chunk coordinates stored in PostgreSQL and retrieved from Qdrant.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 space-y-2">
                <span className="text-[10px] text-zinc-400 block uppercase font-semibold">Actions</span>
                <Link
                  href="/documents"
                  className="inline-flex items-center gap-1.5 text-xs text-accent hover:underline font-medium"
                >
                  <ExternalLink className="w-3 h-3" />
                  Open Document in Catalog
                </Link>
              </div>
            </div>

            <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 text-center">
              <button
                onClick={() => setSelectedCitation(null)}
                className="w-full py-1.5 rounded-md border border-zinc-300 dark:border-zinc-700 text-xs font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800 transition cursor-pointer"
              >
                Close Inspector
              </button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
