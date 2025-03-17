import React from "react";

interface Recommendation {
  id: string;
  title: string;
  filename?: string;
  fileLink?: string;
  original_filename?: string;
  author_name?: string;
  field?: string;
  keywords?: string[];
  meme_type?: string;
  created_at?: string;
}

interface Props {
  recommendations: Recommendation[];
}

export default function RecommendationCarousel({ recommendations }: Props) {
  // This function opens the fileLink in a new tab, if it exists
  const handleOpenFile = (fileLink?: string) => {
    if (!fileLink) {
      alert("No file to open!");
      return;
    }
    window.open(fileLink, "_blank");
  };

  return (
    <div className="mt-8">
      <h2 className="text-xl font-bold mb-2">Recommended for You</h2>
      <div className="flex space-x-4 overflow-x-auto">
        {recommendations.map((doc) => (
          <div
            key={doc.id}
            className="min-w-[200px] bg-white border rounded p-4 shadow-sm"
          >
            <h3 className="font-semibold text-sm">{doc.title}</h3>
            <p className="text-xs text-gray-600 mt-1 line-clamp-3">
              {doc.keywords?.join(", ") || "No keywords"}
            </p>
            <p className="text-xs mt-2 text-blue-600">Field: {doc.field}</p>

            {/* If there's a Google Drive link (fileLink), show a button to open it */}
            {doc.fileLink && (
              <button
                onClick={() => handleOpenFile(doc.fileLink)}
                className="text-blue-500 underline text-xs mt-2"
              >
                View File
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
