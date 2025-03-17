import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/auth";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { Send, SkipForward, Loader } from "lucide-react";

interface QA {
  question: string;
  answer: string;
  skipped?: boolean;
}

export default function ChatQA() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [topic, setTopic] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [conversation, setConversation] = useState<QA[]>([]);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState("");

  // Function to generate AI questions using the backend endpoint
  const generateQuestions = async () => {
    setIsLoading(true);
    try {
      const response = await api.post("/ai/generate-questions", { topic });
      const data = response.data;
      if (data.questions) {
        setQuestions(data.questions);
      } else {
        toast.error("Failed to generate questions");
      }
    } catch (error) {
      toast.error("Error generating questions");
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartChat = () => {
    if (!topic.trim()) {
      toast.error("Please enter a topic");
      return;
    }
    generateQuestions();
  };

  const handleAnswerSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentAnswer.trim()) return;

    const newQA: QA = {
      question: questions[currentQuestionIndex],
      answer: currentAnswer,
    };

    setConversation([...conversation, newQA]);
    setCurrentAnswer("");

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } else {
      // All questions answered, now summarize chat
      summarizeChat();
    }
  };

  const handleSkipQuestion = () => {
    const newQA: QA = {
      question: questions[currentQuestionIndex],
      answer: "Skipped",
      skipped: true,
    };

    setConversation([...conversation, newQA]);

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } else {
      // All questions answered or skipped, now summarize chat
      summarizeChat();
    }
  };

  const summarizeChat = async () => {
    setIsLoading(true);
    try {
      const response = await api.post("/ai/summarize-chat", {
        topic,
        conversation,
      });
      const data = response.data;
      if (data.summary) {
        setSummary(data.summary);
        toast.success("Chat summarized successfully!");
      } else {
        toast.error("Failed to generate summary");
      }
    } catch (error) {
      toast.error("Error summarizing chat");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-3xl font-bold mb-4">
        Chat with AI on {topic || "Your Topic"}
      </h1>
      {!questions.length ? (
        <div className="max-w-xl mx-auto">
          <input
            type="text"
            placeholder="Enter topic..."
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full p-2 border rounded mb-4"
          />
          <button
            onClick={handleStartChat}
            disabled={isLoading}
            className="w-full bg-blue-600 text-white p-2 rounded flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader className="w-5 h-5 animate-spin" />
                <span>Generating Questions...</span>
              </>
            ) : (
              "Start Chat"
            )}
          </button>
        </div>
      ) : isLoading ? (
        <div className="max-w-2xl mx-auto flex flex-col items-center justify-center p-8">
          <Loader className="w-12 h-12 animate-spin text-blue-600 mb-4" />
          <p className="text-lg text-gray-600">
            Generating your chat summary...
          </p>
        </div>
      ) : summary ? (
        <div className="max-w-2xl mx-auto bg-white p-6 rounded shadow">
          <h2 className="text-2xl font-semibold mb-4">Chat Summary</h2>
          <div className="prose max-w-none mb-6">
            <p className="text-gray-700 whitespace-pre-line">{summary}</p>
          </div>
          <div className="flex items-center justify-between">
            <button
              onClick={() => {
                setQuestions([]);
                setConversation([]);
                setSummary("");
                setCurrentQuestionIndex(0);
                setTopic("");
              }}
              className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600 transition-colors"
            >
              Start New Chat
            </button>
            <button
              onClick={() => navigate("/user/dashboard")}
              className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition-colors"
            >
              Continue to Dashboard
            </button>
          </div>
        </div>
      ) : (
        <div className="max-w-2xl mx-auto">
          <div className="bg-white p-6 rounded shadow mb-4">
            <h2 className="text-xl font-semibold mb-2">
              Question {currentQuestionIndex + 1} of {questions.length}
            </h2>
            <p className="mb-4">{questions[currentQuestionIndex]}</p>
            <div className="flex gap-2">
              <form onSubmit={handleAnswerSubmit} className="flex-1">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Type your answer..."
                    value={currentAnswer}
                    onChange={(e) => setCurrentAnswer(e.target.value)}
                    className="flex-1 p-2 border rounded-l"
                  />
                  <button
                    type="submit"
                    className="bg-blue-600 text-white px-4 rounded-r flex items-center"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </form>
              <button
                onClick={handleSkipQuestion}
                className="bg-gray-500 text-white px-4 rounded flex items-center gap-2 hover:bg-gray-600 transition-colors"
                title="Skip this question"
              >
                <SkipForward className="w-5 h-5" />
                Skip
              </button>
            </div>
          </div>
          <div className="bg-gray-100 p-4 rounded">
            <h3 className="font-semibold mb-2">Conversation so far:</h3>
            {conversation.map((qa, index) => (
              <div key={index} className="mb-4 last:mb-0">
                <p className="mb-1">
                  <strong>Q:</strong> {qa.question}
                </p>
                <p>
                  <strong>A:</strong>{" "}
                  <span className={qa.skipped ? "text-gray-500 italic" : ""}>
                    {qa.answer}
                  </span>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
