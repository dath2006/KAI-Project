import React, { useState, useEffect, useRef } from "react";
import { Send, FileText, Download, ExternalLink, X } from "lucide-react";
import DOMPurify from "dompurify";

interface Message {
  id: string;
  text: string;
  sender: "user" | "ai";
  timestamp: Date;
  isLoading?: boolean;
  context?: {
    documents_found: number;
    relevant_topics: string[];
    documents?: Array<{
      title: string;
      original_filename: string;
      field: string;
      viewLink: string;
      fileLink: string;
      doc_type: "document" | "summary";
      summary_content?: string;
    }>;
  };
}

interface SummaryModalProps {
  summary: string;
  onClose: () => void;
}

const SummaryModal: React.FC<SummaryModalProps> = ({ summary, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-[80%] max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold">Chat Summary</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-6 overflow-y-auto">
          <div
            className="prose max-w-none"
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(summary),
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default function ChatWithAI() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [selectedSummary, setSelectedSummary] = useState<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      text: inputMessage,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, newMessage]);
    setInputMessage("");
    setIsLoading(true);

    // Add a loading message
    const loadingMessage: Message = {
      id: "loading-" + Date.now().toString(),
      text: "",
      sender: "ai",
      timestamp: new Date(),
      isLoading: true,
    };
    setMessages((prev) => [...prev, loadingMessage]);

    try {
      const response = await fetch("http://localhost:8080/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ query: inputMessage }),
      });
      const data = await response.json();
      console.log("API Response:", data); // Debug log

      if (response.ok) {
        // Remove loading message and add actual response
        setMessages((prev) => prev.filter((msg) => !msg.isLoading));

        const aiResponse: Message = {
          id: Date.now().toString(),
          text: data.response,
          sender: "ai",
          timestamp: new Date(),
          context: {
            documents_found: data.context.documents_found,
            relevant_topics: data.context.relevant_topics,
            documents: data.context.documents || [],
          },
        };
        console.log("AI Response Object:", aiResponse); // Debug log
        setMessages((prev) => [...prev, aiResponse]);
      } else {
        throw new Error(data.error || "Failed to get response");
      }
    } catch (error) {
      console.error("Error:", error);
      // Remove loading message and add error message
      setMessages((prev) => prev.filter((msg) => !msg.isLoading));
      const errorMessage: Message = {
        id: Date.now().toString(),
        text: "Sorry, I encountered an error. Please try again.",
        sender: "ai",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDocumentClick = (
    doc: NonNullable<NonNullable<Message["context"]>["documents"]>[0]
  ) => {
    if (doc.doc_type === "summary" && doc.summary_content) {
      setSelectedSummary(doc.summary_content);
    } else if (doc.fileLink) {
      window.open(doc.fileLink, "_blank");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="flex-1 max-w-4xl w-full mx-auto p-4">
        <div className="bg-white rounded-lg shadow-sm h-[calc(100vh-2rem)] flex flex-col">
          {/* Chat Header */}
          <div className="p-4 border-b border-gray-200">
            <h1 className="text-xl font-semibold">Chat with AI Assistant</h1>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.sender === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[70%] rounded-lg p-3 ${
                    message.sender === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-900"
                  }`}
                >
                  {message.isLoading ? (
                    <div className="flex items-center space-x-2">
                      <div
                        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "0ms" }}
                      ></div>
                      <div
                        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "150ms" }}
                      ></div>
                      <div
                        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "300ms" }}
                      ></div>
                    </div>
                  ) : (
                    <>
                      <div
                        className={`prose prose-sm max-w-none ${
                          message.sender === "user" ? "prose-invert" : ""
                        }`}
                      >
                        {message.sender === "user" ? (
                          <p>{message.text}</p>
                        ) : (
                          <>
                            <div
                              dangerouslySetInnerHTML={{
                                __html: DOMPurify.sanitize(message.text),
                              }}
                              className="markdown-content [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_p]:mb-2 [&_li]:mb-1 [&_h1]:text-xl [&_h1]:font-bold [&_h1]:mb-2 [&_h2]:text-lg [&_h2]:font-bold [&_h2]:mb-2 [&_h3]:text-base [&_h3]:font-bold [&_h3]:mb-2 [&_blockquote]:border-l-4 [&_blockquote]:border-gray-300 [&_blockquote]:pl-4 [&_blockquote]:italic [&_code]:bg-gray-200 [&_code]:px-1 [&_code]:rounded [&_pre]:bg-gray-800 [&_pre]:text-white [&_pre]:p-2 [&_pre]:rounded [&_pre]:overflow-x-auto [&_table]:border-collapse [&_table]:w-full [&_td,&_th]:border [&_td,&_th]:border-gray-300 [&_td,&_th]:p-2"
                            />
                            {message.context &&
                              message.context.documents_found > 0 && (
                                <div className="mt-3 text-sm border-t border-gray-200 pt-2">
                                  <div className="flex items-center text-gray-600 mb-2">
                                    <FileText className="h-4 w-4 mr-1" />
                                    <p>
                                      Found {message.context.documents_found}{" "}
                                      relevant document(s)
                                    </p>
                                  </div>
                                  {message.context.documents &&
                                    message.context.documents.length > 0 && (
                                      <div className="space-y-2">
                                        {message.context.documents.map(
                                          (doc, index) => (
                                            <div
                                              key={index}
                                              className="bg-gray-50 rounded-lg p-3 hover:bg-gray-100 transition-colors"
                                            >
                                              <div className="flex items-center justify-between">
                                                <div className="flex-1">
                                                  <h4 className="font-medium text-gray-900">
                                                    {doc.doc_type === "summary"
                                                      ? "Chat Summary"
                                                      : doc.original_filename}
                                                  </h4>
                                                  <p className="text-sm text-gray-500">
                                                    {doc.doc_type === "summary"
                                                      ? "Summary"
                                                      : doc.field}
                                                  </p>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                  <button
                                                    onClick={() =>
                                                      handleDocumentClick(doc)
                                                    }
                                                    className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-full transition-colors"
                                                    title={
                                                      doc.doc_type === "summary"
                                                        ? "View Summary"
                                                        : "View Document"
                                                    }
                                                  >
                                                    <ExternalLink className="h-4 w-4" />
                                                  </button>
                                                  {doc.doc_type ===
                                                    "document" && (
                                                    <a
                                                      href={doc.fileLink}
                                                      download
                                                      className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-full transition-colors"
                                                      title="Download Document"
                                                    >
                                                      <Download className="h-4 w-4" />
                                                    </a>
                                                  )}
                                                </div>
                                              </div>
                                            </div>
                                          )
                                        )}
                                      </div>
                                    )}
                                  {message.context.relevant_topics.length >
                                    0 && (
                                    <div className="mt-3">
                                      <p className="text-gray-600 mb-1">
                                        Related topics:
                                      </p>
                                      <div className="flex flex-wrap gap-1">
                                        {message.context.relevant_topics.map(
                                          (topic, index) => (
                                            <span
                                              key={index}
                                              className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full text-xs font-medium"
                                            >
                                              {topic}
                                            </span>
                                          )
                                        )}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                          </>
                        )}
                      </div>
                      <span className="text-xs opacity-75 mt-2 block">
                        {message.timestamp.toLocaleTimeString()}
                      </span>
                    </>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Message Input */}
          <form
            onSubmit={handleSendMessage}
            className="p-4 border-t border-gray-200"
          >
            <div className="flex space-x-4">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Type your message..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isLoading}
              />
              <button
                type="submit"
                className={`bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center ${
                  isLoading ? "opacity-50 cursor-not-allowed" : ""
                }`}
                disabled={isLoading}
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Summary Modal */}
      {selectedSummary && (
        <SummaryModal
          summary={selectedSummary}
          onClose={() => setSelectedSummary(null)}
        />
      )}
    </div>
  );
}
