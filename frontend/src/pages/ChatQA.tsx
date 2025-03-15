import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/auth";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { Send } from "lucide-react";

interface QA {
  question: string;
  answer: string;
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
      <h1 className="text-3xl font-bold mb-4">Chat with AI on {topic || "Your Topic"}</h1>
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
            className="w-full bg-blue-600 text-white p-2 rounded"
          >
            {isLoading ? "Generating Questions..." : "Start Chat"}
          </button>
        </div>
      ) : summary ? (
        <div className="max-w-2xl mx-auto bg-white p-6 rounded shadow">
          <h2 className="text-2xl font-semibold mb-4">Chat Summary</h2>
          <p>{summary}</p>
          <button
            onClick={() => navigate("/user/dashboard")}
            className="mt-4 bg-blue-600 text-white px-4 py-2 rounded"
          >
            Back to Dashboard
          </button>
        </div>
      ) : (
        <div className="max-w-2xl mx-auto">
          <div className="bg-white p-6 rounded shadow mb-4">
            <h2 className="text-xl font-semibold mb-2">
              Question {currentQuestionIndex + 1} of {questions.length}
            </h2>
            <p className="mb-4">{questions[currentQuestionIndex]}</p>
            <form onSubmit={handleAnswerSubmit} className="flex">
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
            </form>
          </div>
          <div className="bg-gray-100 p-4 rounded">
            <h3 className="font-semibold mb-2">Conversation so far:</h3>
            {conversation.map((qa, index) => (
              <div key={index} className="mb-2">
                <p>
                  <strong>Q:</strong> {qa.question}
                </p>
                <p>
                  <strong>A:</strong> {qa.answer}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
